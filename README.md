# Skill MatchAI

A Flask web app that compares skills in a resume with those in a job description. It extracts skills using a Groq language model, shows the matches, and calculates a matching score.

## Features

- Accepts PDF, DOCX, and DOC resumes (maximum 10 MB).
- Displays skills found in the resume and job description, matched skills, and a score out of 100.
- Suggests a result based on the score: shortlist (60+), human review (30–59), or reject (under 30).

## Setup

1. Install Python.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Set your Groq API key in PowerShell:

   ```powershell
   $env:GROQ_API_KEY = "your_groq_api_key"
   ```

   Get an API key from [Groq](https://console.groq.com/). Keep it private and do not commit it to GitHub.

5. Start the app:

   ```powershell
   python app.py
   ```

6. Open the local address shown in the terminal (usually `http://127.0.0.1:5000`).

The legacy `.doc` format also requires `antiword` to be installed and available on your system's PATH. PDF and DOCX files do not require it.

## Privacy

Uploaded resumes and job descriptions are sent to the configured Groq model for skill extraction. Use only documents you are authorized to process, and do not deploy the Flask development server (`debug=True`) as a production service.
