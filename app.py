from flask import Flask, render_template, request, jsonify, send_file
import fitz  # PyMuPDF
import os
from dotenv import load_dotenv
from together import Together
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from io import BytesIO
import re
import json
from datetime import datetime, timedelta


app = Flask(__name__)
load_dotenv()

# ✅ Load Together API key from .env
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# ✅ Initialize Together client
client = Together(api_key=TOGETHER_API_KEY)

@app.route('/teacher')
def teacher():
    return render_template('teacher.html')


@app.route('/')
def index():
    return render_template('v3.html')


@app.route('/time')
def time():
    return render_template('time.html')


@app.route('/smart')
def smart_page():
    return render_template('smart.html')
@app.route('/api/generate-schedule', methods=['POST'])
def generate_schedule():
    """Generate AI-powered study schedule from uploaded PDFs"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract parameters
        exam_date = data.get('examDate', '')
        daily_hours = data.get('dailyHours', 2)
        study_preference = data.get('studyPreference', 'balanced')  # theory-heavy, practice-heavy, balanced
        summary_text = data.get('summaryText', '')
        source_text = data.get('sourceText', '')
        
        if not exam_date:
            return jsonify({"error": "Exam date is required"}), 400
        
        if not summary_text and not source_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Build context
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
        
        # AI prompt for schedule generation
        system_prompt = (
            "You are an expert study planner AI. Create realistic, effective study schedules based on document content. "
            "Output ONLY valid JSON, no markdown formatting, no extra text."
        )
        
        user_prompt = f"""Create a detailed study schedule with this information:

CONTENT TO STUDY:
{context}

CONSTRAINTS:
- Exam date: {exam_date}
- Daily available hours: {daily_hours}
- Study preference: {study_preference}

Generate a JSON schedule with this EXACT structure:
{{
  "title": "AI Study Plan for [Subject]",
  "totalTopics": [number],
  "examDate": "{exam_date}",
  "dailyHours": {daily_hours},
  "schedule": [
    {{
      "day": 1,
      "date": "2025-10-09",
      "topics": [
        {{
          "time": "10:00 AM - 11:00 AM",
          "topic": "Topic Name",
          "description": "Brief description",
          "type": "theory",
          "music": "lofi"
        }}
      ],
      "goals": ["Goal 1", "Goal 2", "Goal 3"]
    }}
  ],
  "cheatSheets": [
    {{
      "title": "Quick Reference - Topic Name",
      "content": "Key formulas, definitions, or concepts",
      "type": "formulas"
    }}
  ]
}}

RULES:
1. Extract key topics from the document content
2. Distribute topics across days leading up to exam date
3. Balance theory (40%), practice (40%), and review (20%) for "balanced" preference
4. Each day should have {daily_hours} hours total of study time
5. Include realistic time slots (e.g., "10:00 AM - 11:00 AM")
6. type can be: "theory", "practice", or "review"
7. music can be: "lofi", "classical", "nature", "instrumental", or "focus"
8. Create 3-5 daily goals per day
9. Generate 3-5 cheat sheets with condensed key information
10. Return ONLY the JSON, no markdown code blocks

Output the complete JSON now:"""

        # Call Together AI
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3000,
            temperature=0.5
        )
        
        schedule_json_str = response.choices[0].message.content.strip()
        
        # Clean up response - remove markdown code blocks if present
        schedule_json_str = re.sub(r'^```json\s*', '', schedule_json_str)
        schedule_json_str = re.sub(r'^```\s*', '', schedule_json_str)
        schedule_json_str = re.sub(r'\s*```$', '', schedule_json_str)
        schedule_json_str = schedule_json_str.strip()
        
        # Parse JSON
        import json
        schedule_data = json.loads(schedule_json_str)
        
        return jsonify(schedule_data)
        
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Failed to parse AI response as JSON",
            "details": str(e),
            "raw_response": schedule_json_str[:500]  # First 500 chars for debugging
        }), 500
    except Exception as e:
        return jsonify({"error": f"Schedule generation failed: {str(e)}"}), 500

@app.route('/api/schedule', methods=['POST'])
def schedule_api():
    """Alias route used by frontend to generate schedules (same as /api/generate-schedule)."""
    return generate_schedule()


@app.route('/api/download-cheatsheet', methods=['POST'])
def download_cheatsheet():
    """Generate and download a cheat sheet PDF"""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'Study Cheat Sheet')
        content = data.get('content', '')
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              topMargin=0.5*inch, bottomMargin=0.5*inch,
                              leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#2563eb',
            spaceAfter=12,
            alignment=TA_LEFT
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=6
        )
        
        # Build PDF content
        story = []
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Split content into paragraphs and add to PDF
        for paragraph in content.split('\n\n'):
            if paragraph.strip():
                # Handle markdown-style bold
                paragraph = paragraph.replace('**', '<b>').replace('**', '</b>')
                story.append(Paragraph(paragraph.strip(), body_style))
                story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{title.replace(" ", "_")}.pdf'
        )
        
    except Exception as e:
        return jsonify({"error": f"Cheat sheet generation failed: {str(e)}"}), 500
# Add these routes to your app.py file

@app.route('/flash')
def flash():
    """Flashcards page route"""
    return render_template('flash.html')


@app.route('/api/generate-flashcards', methods=['POST'])
def generate_flashcards():
    """Generate AI-powered flashcards from document content"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract parameters
        summary_text = data.get('summaryText', '')
        source_text = data.get('sourceText', '')
        difficulty = data.get('difficulty', 'medium')  # easy, medium, hard
        count = data.get('count', 20)  # number of flashcards
        
        if not summary_text and not source_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Build context
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
        
        # Difficulty settings
        difficulty_settings = {
            'easy': {
                'description': 'Basic recall questions with straightforward answers',
                'question_style': 'Simple definitions and basic concept identification',
                'answer_length': '1-2 sentences'
            },
            'medium': {
                'description': 'Application-based questions requiring understanding',
                'question_style': 'How/Why questions and concept connections',
                'answer_length': '2-3 sentences with brief explanations'
            },
            'hard': {
                'description': 'Analysis and synthesis questions requiring deep understanding',
                'question_style': 'Compare/contrast, analyze, evaluate questions',
                'answer_length': '3-4 sentences with detailed reasoning'
            }
        }
        
        settings = difficulty_settings.get(difficulty, difficulty_settings['medium'])
        
        # AI prompt for flashcard generation
        system_prompt = (
            "You are an expert educational content creator specializing in creating effective flashcards. "
            "Create flashcards that promote active recall and spaced repetition. "
            "Output ONLY valid JSON, no markdown formatting, no extra text."
        )
        
        user_prompt = f"""Create {count} high-quality flashcards from the following content:

CONTENT:
{context}

DIFFICULTY: {difficulty.upper()}
- {settings['description']}
- Question style: {settings['question_style']}
- Answer length: {settings['answer_length']}

Generate a JSON response with this EXACT structure:
{{
  "flashcards": [
    {{
      "id": 1,
      "question": "Clear, specific question",
      "answer": "Concise, accurate answer",
      "category": "Topic/Category name",
      "difficulty": "{difficulty}",
      "hint": "Optional hint (can be empty string)"
    }}
  ],
  "metadata": {{
    "totalCards": {count},
    "difficulty": "{difficulty}",
    "categories": ["Category 1", "Category 2", "..."]
  }}
}}

RULES:
1. Create exactly {count} flashcards
2. Questions must be clear, specific, and promote recall
3. Answers must be accurate and concise ({settings['answer_length']})
4. Distribute flashcards across 3-5 logical categories from the content
5. Each flashcard must have: id, question, answer, category, difficulty, hint
6. Hints should be brief (5-10 words) or empty string if not needed
7. Ensure variety in question types (definitions, applications, comparisons, etc.)
8. Return ONLY the JSON, no markdown code blocks

Output the complete JSON now:"""

        # Call Together AI
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3500,
            temperature=0.6
        )
        
        flashcards_json_str = response.choices[0].message.content.strip()
        
        # Clean up response - remove markdown code blocks if present
        flashcards_json_str = re.sub(r'^```json\s*', '', flashcards_json_str)
        flashcards_json_str = re.sub(r'^```\s*', '', flashcards_json_str)
        flashcards_json_str = re.sub(r'\s*```$', '', flashcards_json_str)
        flashcards_json_str = flashcards_json_str.strip()
        
        # Parse JSON
        flashcard_data = json.loads(flashcards_json_str)
        
        return jsonify(flashcard_data)
        
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Failed to parse AI response as JSON",
            "details": str(e),
            "raw_response": flashcards_json_str[:500] if 'flashcards_json_str' in locals() else ""
        }), 500
    except Exception as e:
        return jsonify({"error": f"Flashcard generation failed: {str(e)}"}), 500

@app.route('/api/process', methods=['POST'])
def process_pdf():
    # Extract file from either 'file' or 'files' field
    if 'file' in request.files:
        file = request.files['file']
    elif 'files' in request.files:
        files_list = request.files.getlist('files')
        file = files_list[0] if files_list else None
    else:
        return jsonify({"error": "No file uploaded. Send as 'file' or 'files'."}), 400

    if file is None or file.filename == '':
        return jsonify({"error": "Empty file upload."}), 400

    # Extract text from PDF
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    # Guard clause: handle empty PDFs
    if not text.strip():
        return jsonify({"error": "No text found in the uploaded PDF."}), 400

    # ✅ Get AI summary from Together model with longer, well-spaced Markdown
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": (
                    "You are an expert document analyst who creates well-structured, comprehensive summaries. "
                    "Your summaries are organized, clear, and easy to scan, with excellent spacing."
                )},
                {"role": "user", "content": (
                    f"Create a comprehensive summary of the following document. Follow this structure:\n\n"
                    f"1. Start with a clear **Topic/Main Subject** heading (NOT the speaker's name).\n"
                    f"2. Provide 15-25 well-organized bullet points that:\n"
                    f"   - Cover key concepts, important details, and notable examples\n"
                    f"   - Group related ideas together logically\n"
                    f"   - Include brief definitions and short process steps where relevant\n"
                    f"   - Use sub-bullets for supporting details when needed\n\n"
                    f"Formatting rules (Markdown):\n"
                    f"- Use bold for mini section headers (e.g., **Key challenges**, **Approach**).\n"
                    f"- Use hyphen bullets and include blank lines between major bullets for readability.\n"
                    f"- Prefer short paragraphs; avoid walls of text.\n"
                    f"- Ensure the summary is complete and non-truncated.\n\n"
                    f"Aim for slightly more detail rather than less (but stay concise).\n\n"
                    f"Document text:\n\n{text}"
                )}
            ],
            max_tokens=2200,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
    except Exception as e:
        return jsonify({"error": f"AI processing failed: {str(e)}"}), 500

    # Shape response for frontend expectations
    return jsonify({
        "result": summary or "",
        "source_text": text or "",
        "doc_title": file.filename or "Document"
    })


@app.route('/api/smart_summary', methods=['POST'])
def smart_summary():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    level = int(data.get('level') or 1)
    title = (data.get('title') or 'Document').strip()

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    level = max(1, min(level, 3))

    # Scale factors based on level: 1x, 2x, 5x, 8x (deep understanding)
    scale_map = {1: 1, 2: 2, 3: 5, 4: 8}
    detail_scale = scale_map.get(level, 1)

    base = {
        "topics_min": 8,
        "topics_max": 12,
        "qa_min": 5,
        "qa_max": 8,
        "notes_min": 4,
        "notes_max": 6
    }

    def scaled(a):
        return int(round(a * detail_scale))

    topics_min = max(6, min(60, scaled(base["topics_min"])))
    topics_max = max(topics_min + 2, min(80, scaled(base["topics_max"])))
    qa_min = max(4, min(50, scaled(base["qa_min"])))
    qa_max = max(qa_min + 2, min(70, scaled(base["qa_max"])))
    notes_min = max(3, min(30, scaled(base["notes_min"])))
    notes_max = max(notes_min + 1, min(40, scaled(base["notes_max"])))

    level_specs = {
        1: {
            "label": "Level 1 - Essentials",
            "instructions": (
                "Keep the SAME structure as higher levels but shorter wording. Sections: **Important Topics**, **Q&A**, **Must-Remember Notes**.\n"
                f"- Important Topics: {topics_min}-{topics_max} bullets\n"
                f"- Q&A: {qa_min}-{qa_max} pairs, 1-3 sentence answers\n"
                f"- Must-Remember Notes: {notes_min}-{notes_max} bullets\n"
                "Use Markdown; blank lines between major bullets. Prefer brevity but include substance."
            ),
            "max_tokens": min(2800, 800 + topics_max * 20 + qa_max * 40)
        },
        2: {
            "label": "Level 2 - Detailed",
            "instructions": (
                "Same sections as Level 1 with roughly 2x detail and a bit more examples.\n"
                f"- Important Topics: {topics_min}-{topics_max} bullets with brief definitions/examples\n"
                f"- Q&A: {qa_min}-{qa_max} pairs with concise rationale\n"
                f"- Must-Remember Notes: {notes_min}-{notes_max} bullets\n"
                "Use sub-bullets when helpful; keep paragraphs short."
            ),
            "max_tokens": min(3200, 1200 + topics_max * 30 + qa_max * 60)
        },
        3: {
            "label": "Level 3 - Super Detailed",
            "instructions": (
                "Same sections but 5x detail overall. Include brief rationale/why and process steps when relevant.\n"
                f"- Important Topics: {topics_min}-{topics_max} bullets with sub-bullets\n"
                f"- Q&A: {qa_min}-{qa_max} pairs with high-yield explanations\n"
                f"- Must-Remember Notes: {notes_min}-{notes_max} bullets\n"
                "Keep everything scannable with spacing; avoid walls of text."
            ),
            "max_tokens": min(3800, 1500 + topics_max * 40 + qa_max * 80)
        },
        4: {
            "label": "Level 4 - Deep Understanding",
            "instructions": (
                "Deep-dive study guide with the SAME sections but the richest coverage. Add concise rationale, tradeoffs, and pitfalls.\n"
                f"- Important Topics: {topics_min}-{topics_max} bullets with sub-bullets and mini examples\n"
                f"- Q&A: {qa_min}-{qa_max} pairs with nuanced answers\n"
                f"- Must-Remember Notes: {notes_min}-{notes_max} bullets (mnemonics if useful)\n"
                "Keep paragraphs short and readable."
            ),
            "max_tokens": min(4200, 1800 + topics_max * 45 + qa_max * 90)
        }
    }

    spec = level_specs[level]

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": (
                    "You are an expert study guide writer. Output valid Markdown with good spacing."
                )},
                {"role": "user", "content": (
                    f"Create a {spec['label']} for: {title}.\n\n"
                    f"Instructions:\n{spec['instructions']}\n\n"
                    f"Source text (quote and condense as needed):\n\n{text}"
                )}
            ],
            max_tokens=spec["max_tokens"],
            temperature=0.3
        )

        result = response.choices[0].message.content
        return jsonify({"result": result or ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    context_text = (data.get('summary_text') or '').strip()
    source_text = (data.get('source_text') or '').strip()
    mode = (data.get('mode') or 'professor').strip()

    if not question:
        return jsonify({"error": "Missing 'question'"}), 400

    system_prompt = (
        "You are an expert professor who explains concepts clearly with structure, examples, and step-by-step reasoning. "
        "You have access to both a summary and the full document text. Use both to provide comprehensive, accurate answers. "
        "Always cite specific concepts from the context. If the answer is not in the provided context, say so explicitly."
    ) if mode == 'professor' else (
        "You are a helpful assistant with access to document context."
    )

    # Build context from both summary and source text
    full_context = ""
    if context_text:
        full_context += f"DOCUMENT SUMMARY:\n{context_text}\n\n"
    if source_text:
        full_context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
    
    if not full_context:
        full_context = "No context provided."

    user_prompt = (
        f"{full_context}"
        f"QUESTION: {question}\n\n"
        f"Instructions:\n"
        f"- Answer based on the provided summary AND full document text\n"
        f"- Reference specific concepts, facts, or sections from the context\n"
        f"- If solving a problem, show your step-by-step work\n"
        f"- Be concise but complete\n"
        f"- If the answer isn't in the context, state that clearly"
    )

    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.4
        )

        answer = response.choices[0].message.content if response and response.choices else ""
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)