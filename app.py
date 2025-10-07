from flask import Flask, render_template, request, jsonify, redirect, url_for
import fitz
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__, template_folder='templates', static_folder='static')

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")

# ---------- ROUTES ----------
@app.route('/')
def index():
    return redirect(url_for('v3'))

@app.route('/v3')
def v3():
    return render_template('v3.html')


# ---------- AI SUMMARIZER ----------
def generate_summary(text: str) -> str:
    prompt = f"""
You are an expert educator. Turn the following text into a concise, HTML-formatted study summary.
Use only HTML tags like <section>, <h2>, <p>, <ul>, <li>, <strong>.
Keep it structured and easy to read.
-----
{text}
-----
"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
    }
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()['choices'][0]['message']['content']


@app.route('/api/process', methods=['POST'])
def process_pdfs():
    files = request.files.getlist('files')
    combined_text = ""
    for f in files:
        doc = fitz.open(stream=f.read(), filetype="pdf")
        for page in doc:
            combined_text += page.get_text()

    html_summary = generate_summary(combined_text)
    return jsonify({"result": html_summary, "source_text": combined_text})


# ---------- CHAT FUNCTION ----------
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question', '')
    summary_text = data.get('summary_text', '')

    prompt = f"""
Answer this question using ONLY the context below.
If not found, say you don't have enough info.

CONTEXT:
{summary_text}

QUESTION:
{question}
"""

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
    }
    resp = requests.post(url, headers=headers, json=payload)
    return jsonify({"response": resp.json()['choices'][0]['message']['content']})


if __name__ == '__main__':
    app.run(debug=True)
