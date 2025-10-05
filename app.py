from flask import Flask, render_template, request, jsonify
import fitz
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__, template_folder='template')

@app.route('/')
def index():
    return render_template('index.html')

load_dotenv()  # Load variables from .env into environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

def generate_outputs(text: str) -> str:
    prompt = f"""
    You are an expert educator. Take the following text and generate:

    1. A concise structured summary (with headings and bullet points)
    2. 5 flashcards in Q&A format
    3. 5 multiple-choice quiz questions with answers
    4. A short 2-minute presentation script

    Text:
    {text}

    Output each section clearly labeled.
    """

    try:
        if not GEMINI_API_KEY:
            return "GEMINI_API_KEY is not set. Create a .env file with GEMINI_API_KEY=your_key and restart the app."
        # Trim very long inputs to keep within token limits (approximate safeguard)
        if len(text) > 20000:
            text = text[:20000] + "\n\n...[truncated]"

        url = (
            "https://generativelanguage.googleapis.com/v1/models/"
            f"{GEMINI_MODEL}:generateContent?key=" + GEMINI_API_KEY
        )
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        if resp.status_code != 200:
            return f"Gemini API error {resp.status_code}: {data}"
        # Parse Gemini response
        result = (
            data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text")
        )
        return result or "[No response]"
    except Exception as e:
        return f"Error generating AI output: {e}"

@app.route('/api/process', methods=['POST'])
def process_pdfs():
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "No files uploaded"}), 400
        if len(files) > 5:
            return jsonify({"error": "Maximum of 5 files allowed"}), 400

        combined_text = ""
        for f in files:
            filename = f.filename or ""
            if not filename.lower().endswith('.pdf'):
                return jsonify({"error": f"Unsupported file type for {filename}. Only PDF is allowed."}), 400
            doc = fitz.open(stream=f.read(), filetype="pdf")
            for page in doc:
                combined_text += page.get_text()

        if not combined_text.strip():
            return jsonify({"error": "No extractable text found in PDFs"}), 400

        ai_output = generate_outputs(combined_text)
        return jsonify({"result": ai_output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
