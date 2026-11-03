
import os
import tempfile
import subprocess
from io import BytesIO
from typing import TypedDict
from dotenv import load_dotenv
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

from pypdf import PdfReader
from docx import Document

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

load_dotenv()
app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.1
)


####################################################
# RESUME FILE EXTRACTION
####################################################

def extract_resume(file):

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower()

    file_bytes = file.read()

    if extension == "pdf":

        reader = PdfReader(BytesIO(file_bytes))

        content = ""

        for page in reader.pages:
            content += page.extract_text() or ""

        return content

    elif extension == "docx":

        document = Document(BytesIO(file_bytes))

        return "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )

    elif extension == "doc":

        with tempfile.NamedTemporaryFile(
            suffix=".doc", delete=False
        ) as temp:

            temp.write(file_bytes)
            temp_path = temp.name

        try:
            result = subprocess.run(
                ["antiword", temp_path],
                capture_output=True,
                text=True,
                check=True
            )

            return result.stdout

        finally:
            os.remove(temp_path)

    else:
        raise ValueError("Unsupported file format")


####################################################
# STATE
####################################################

class ResumeState(TypedDict):
    resume: str
    jd: str
    skills: list
    jd_skills: list
    matched_skills: list
    score: int
    decision: str


####################################################
# NODE 1: EXTRACT SKILLS
####################################################

def extract_skills(state):

    prompt = f"""
    Extract all technical skills from this resume.

    Return only comma-separated skill names.
    Use standard abbreviations where appropriate.

    Resume:
    {state["resume"]}
    """

    response = llm.invoke(prompt)

    resume_skills = [
        skill.strip()
        for skill in response.content.split(",")
        if skill.strip()
    ]

    state["skills"] = resume_skills

    prompt = f"""
    Extract all technical skills from this job description.

    Return only comma-separated skill names.

    Job Description:
    {state["jd"]}
    """

    response = llm.invoke(prompt)

    jd_skills = [
        skill.strip()
        for skill in response.content.split(",")
        if skill.strip()
    ]

    state["jd_skills"] = jd_skills

    return state


####################################################
# NODE 2: COMPARE JD
####################################################

def compare_jd(state):

    resume_skills = state["skills"]
    jd_skills = state["jd_skills"]

    matched = []

    for skill in resume_skills:

        for jd_skill in jd_skills:

            if skill.lower() == jd_skill.lower():

                if skill not in matched:
                    matched.append(skill)

    score = min(len(matched) * 15, 100)

    state["matched_skills"] = matched
    state["score"] = score

    return state


####################################################
# NODE 3: MAKE DECISION
####################################################

def make_decision(state):

    score = state["score"]

    if score >= 60:
        state["decision"] = "shortlist"

    elif score >= 30:
        state["decision"] = "human_review"

    else:
        state["decision"] = "reject"

    return state


####################################################
# ROUTER
####################################################

def route_decision(state):

    return state["decision"]


####################################################
# FINAL NODES
####################################################

def shortlist(state):
    return state


def reject(state):
    return state


def human_review(state):
    return state


####################################################
# BUILD GRAPH
####################################################

builder = StateGraph(ResumeState)

builder.add_node("extract_skills", extract_skills)
builder.add_node("compare_jd", compare_jd)
builder.add_node("make_decision", make_decision)

builder.add_node("shortlist", shortlist)
builder.add_node("reject", reject)
builder.add_node("human_review", human_review)

builder.set_entry_point("extract_skills")

builder.add_edge("extract_skills", "compare_jd")
builder.add_edge("compare_jd", "make_decision")

builder.add_conditional_edges(
    "make_decision",
    route_decision,
    {
        "shortlist": "shortlist",
        "reject": "reject",
        "human_review": "human_review"
    }
)

builder.add_edge("shortlist", END)
builder.add_edge("reject", END)
builder.add_edge("human_review", END)

graph = builder.compile()


####################################################
# FLASK ROUTES
####################################################

@app.route("/", methods=["GET", "POST"])
def home():

    result = None
    error = None

    if request.method == "POST":

        try:

            resume_file = request.files.get("resume")
            jd = request.form.get("jd", "")

            if not resume_file or not resume_file.filename:
                raise ValueError("Please upload a resume.")

            if not jd.strip():
                raise ValueError("Please enter a job description.")

            extension = resume_file.filename.rsplit(
                ".", 1
            )[-1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                raise ValueError("Only PDF, DOC and DOCX files are supported.")

            content = extract_resume(resume_file)

            if not content.strip():
                raise ValueError("Could not extract text from the resume.")

            result = graph.invoke(
                {
                    "resume": content,
                    "jd": jd,
                    "skills": [],
                    "jd_skills": [],
                    "matched_skills": [],
                    "score": 0,
                    "decision": ""
                }
            )

        except Exception as e:

            error = str(e)

    return render_template(
        "index.html",
        result=result,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)
