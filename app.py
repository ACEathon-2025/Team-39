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
from gtts import gTTS
import requests


app = Flask(__name__)
load_dotenv()
from elevenlabs import ElevenLabs

# Initialize ElevenLabs client (if API key exists)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
eleven_client = None
if ELEVENLABS_API_KEY:
    try:
        eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        print("✅ ElevenLabs client initialized")
    except Exception as e:
        print(f"⚠️ ElevenLabs initialization failed: {e}")

# ✅ Load Together API key from .env
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
# ✅ Load ElevenLabs API key (used in conditionals and client init)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# ✅ Initialize Together client
client = Together(api_key=TOGETHER_API_KEY)

def extract_json_object(text: str):
    """Best-effort extraction of the first top-level JSON object from a text blob."""
    if not text:
        return None
    # Remove common code fences
    cleaned = re.sub(r'^```json\s*', '', text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    cleaned = cleaned.strip()
    # Find first '{' and last '}' to isolate an object
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = cleaned[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        # Last resort: remove trailing commas
        candidate2 = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            return json.loads(candidate2)
        except Exception:
            return None

@app.route('/teacher')
def teacher():
    return render_template('teacher.html')

@app.route('/teacherv2')
def teacherv2():
    return render_template('teacherv2.html')


@app.route('/')
def index():
    return render_template('v3.html')

@app.route('/time')
def time():
    return render_template('time.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/res')
def res():
    return render_template('res.html')

@app.route('/about')
def about():
    """Simple About Us page"""
    return render_template('about.html')

@app.route('/api/generate-professor-slides', methods=['POST'])
def generate_professor_slides():
    """Generate AI-powered teaching slides with deep, detailed content"""
    try:
        data = request.get_json(silent=True) or {}
        
        summary_text = data.get('summaryText', '')
        slide_count = data.get('slideCount', 5)
        teaching_style = data.get('teachingStyle', 'comprehensive')
        
        if not summary_text:
            return jsonify({"error": "No content provided"}), 400
        
        # Teaching style configurations
        style_configs = {
            'comprehensive': {
                'approach': 'Provide thorough explanations with multiple examples, analogies, and step-by-step breakdowns',
                'depth': 'Deep dive into concepts with historical context, practical applications, and theoretical foundations',
                'tone': 'Academic but accessible, like a passionate university professor'
            },
            'storytelling': {
                'approach': 'Frame concepts as narratives with characters, conflicts, and resolutions',
                'depth': 'Use real-world scenarios, case studies, and journey-based explanations',
                'tone': 'Engaging and dramatic, building anticipation and excitement'
            },
            'socratic': {
                'approach': 'Pose thought-provoking questions and guide learners to discover answers',
                'depth': 'Challenge assumptions, explore implications, and develop critical thinking',
                'tone': 'Inquisitive and contemplative, encouraging reflection'
            },
            'technical': {
                'approach': 'Precise definitions, mathematical foundations, and systematic explanations',
                'depth': 'Rigorous analysis with formulas, proofs, and technical specifications',
                'tone': 'Professional and exact, emphasizing accuracy and completeness'
            }
        }
        
        style_config = style_configs.get(teaching_style, style_configs['comprehensive'])
        
        system_prompt = (
            "You are a master educator who creates exceptional teaching content. "
            "Your slides are comprehensive, engaging, and designed to maximize learning. "
            "Output ONLY valid JSON, no markdown formatting."
        )
        
        user_prompt = f"""Create {slide_count} deeply educational slides for a professor-led lecture.

CONTENT TO TEACH:
{summary_text}

TEACHING STYLE: {teaching_style.upper()}
- Approach: {style_config['approach']}
- Depth: {style_config['depth']}
- Tone: {style_config['tone']}

Generate a JSON response with this EXACT structure:
{{
  "slides": [
    {{
      "slideNumber": 1,
      "title": "Clear, Descriptive Title",
      "content": [
        "First teaching point - detailed explanation (2-3 sentences)",
        "Second teaching point - with examples and context (2-3 sentences)",
        "Third teaching point - connecting to previous concepts (2-3 sentences)",
        "Fourth teaching point - practical applications (2-3 sentences)"
      ],
      "narration": "Complete spoken script for this slide. This is what the professor will actually SAY - make it natural, conversational, and thorough. Include transitions, emphasis points, and engaging language. Should be 200-300 words for proper pacing.",
      "example": {{
        "title": "🎯 Real-World Example",
        "content": "Concrete example that illustrates the concept"
      }},
      "visuals": [
        {{
          "icon": "📊",
          "title": "Visual Element 1",
          "description": "Brief description"
        }},
        {{
          "icon": "🔬",
          "title": "Visual Element 2",
          "description": "Brief description"
        }}
      ],
      "keyTakeaway": "One crucial insight from this slide"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. Each slide should have 4-6 content points
2. The "narration" field is THE ACTUAL SPOKEN SCRIPT (200-300 words per slide)
3. Use analogies, examples, and clear explanations
4. Build concepts progressively across slides
5. Include at least 1 example per slide
6. Use appropriate emojis for visual icons
7. Return ONLY the JSON, no markdown code blocks

Output the complete JSON now:"""

        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                temperature=0.3
            )
        except Exception as e:
            return jsonify({"error": f"Slides generation failed: {str(e)}"}), 500
        
        slides_json_str = response.choices[0].message.content.strip()
        
        # Robust JSON extraction
        slide_data = extract_json_object(slides_json_str)
        if not slide_data or 'slides' not in slide_data:
            return jsonify({
                "error": "Failed to parse AI response as JSON",
                "raw_response": slides_json_str[:800]
            }), 500
        
        return jsonify(slide_data)
        
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Failed to parse AI response as JSON",
            "details": str(e),
            "raw_response": slides_json_str[:500] if 'slides_json_str' in locals() else ""
        }), 500
    except Exception as e:
        return jsonify({"error": f"Slide generation failed: {str(e)}"}), 500


@app.route('/api/generate-professor-audio', methods=['POST'])
def generate_professor_audio():
    """Generate TTS audio for the complete professor lecture with timestamps"""
    try:
        data = request.get_json(silent=True) or {}
        
        slides = data.get('slides', [])
        voice_id = data.get('voiceId', '21m00Tcm4TlvDq8ikWAM')  # Default to Rachel
        teaching_style = data.get('teachingStyle', 'comprehensive')
        
        if not slides:
            return jsonify({"error": "No slides provided"}), 400
        
        # Build complete narration script with slide markers
        full_script = ""
        timestamps = []
        current_time = 0.0
        
        for i, slide in enumerate(slides):
            narration = slide.get('narration', '')
            
            # Add slide marker and timestamp
            timestamps.append({
                'slideIndex': i,
                'start': current_time,
                'title': slide.get('title', f'Slide {i+1}')
            })
            
            # Add intro for each slide (except first)
            if i > 0:
                full_script += f"\n\n[Slide {i+1}] "
            
            full_script += narration
            
            # Estimate duration (average speaking rate: 150 words per minute)
            word_count = len(narration.split())
            duration_seconds = (word_count / 150) * 60
            current_time += duration_seconds
            
            # Add brief pause between slides (2 seconds)
            if i < len(slides) - 1:
                full_script += " ... "
                current_time += 2.0
        
        # ✅ FIXED: Better error handling and fallback logic
        os.makedirs("static/audio", exist_ok=True)
        
        # Try ElevenLabs first if client is available
        if eleven_client and ELEVENLABS_API_KEY:
            try:
                print(f"Attempting ElevenLabs TTS with voice: {voice_id}")
                
                audio = eleven_client.text_to_speech.convert(
                    voice_id=voice_id,
                    model_id="eleven_turbo_v2",
                    text=full_script,
                    output_format="mp3_44100_128"
                )

                filename = f"professor_{int(datetime.now().timestamp())}.mp3"
                filepath = os.path.join("static/audio", filename)
                
                with open(filepath, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)

                audio_url = f"/static/audio/{filename}"
                
                return jsonify({
                    "message": "Professor audio generated successfully (ElevenLabs)",
                    "audioUrl": audio_url,
                    "timestamps": timestamps,
                    "totalDuration": current_time,
                    "voiceId": voice_id,
                    "script": full_script
                })
                
            except Exception as e:
                print(f"ElevenLabs failed: {str(e)}, falling back to gTTS")
                # Fall through to gTTS
        
        # Fallback to gTTS
        print("Using gTTS fallback")
        tts = gTTS(text=full_script, lang='en', slow=False)
        filename = f"professor_gtts_{int(datetime.now().timestamp())}.mp3"
        filepath = os.path.join("static/audio", filename)
        tts.save(filepath)
        
        audio_url = f"/static/audio/{filename}"
        
        return jsonify({
            "message": "Professor audio generated successfully (gTTS fallback)",
            "audioUrl": audio_url,
            "timestamps": timestamps,
            "totalDuration": current_time,
            "voiceId": "gtts",
            "script": full_script
        })
        
    except Exception as e:
        print(f"Audio generation error: {str(e)}")
        return jsonify({"error": f"Audio generation failed: {str(e)}"}), 500
    

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
        study_preference = data.get('studyPreference', 'balanced')
        summary_text = data.get('summaryText', '')
        source_text = data.get('sourceText', '')
        
        if not exam_date:
            return jsonify({"error": "Exam date is required"}), 400
        
        # Fallback: allow direct PDF upload (multipart/form-data)
        if not summary_text and not source_text:
            uploaded_file = None
            if 'file' in request.files:
                uploaded_file = request.files['file']
            elif 'files' in request.files:
                files_list = request.files.getlist('files')
                uploaded_file = files_list[0] if files_list else None

            if uploaded_file and uploaded_file.filename:
                try:
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    extracted = []
                    for page in doc:
                        extracted.append(page.get_text())
                    source_text = "\n".join(extracted).strip()
                except Exception as pe:
                    return jsonify({
                        "error": f"Failed to read uploaded PDF: {str(pe)}"
                    }), 400

        if not summary_text and not source_text:
            return jsonify({
                "error": "No document content provided",
                "hint": "Pass summaryText/sourceText as JSON or upload a PDF in 'file'"
            }), 400
        
        # Build context
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
        
        # AI prompt for schedule generation
        system_prompt = (
            "You are an expert study planner AI that outputs ONLY valid JSON. "
            "CRITICAL: Return pure JSON with NO markdown code blocks, NO explanations, NO extra text. "
            "Start your response with { and end with }."
        )
        
        user_prompt = f"""Create a study schedule. Output ONLY the JSON below (no ```json, no markdown):

CONTENT TO STUDY:
{context[:3000]}

CONSTRAINTS:
- Exam date: {exam_date}
- Daily hours: {daily_hours}
- Preference: {study_preference}

Required JSON structure (output THIS EXACT format):
{{
  "title": "Study Plan for [Subject from content]",
  "totalTopics": 10,
  "examDate": "{exam_date}",
  "dailyHours": {daily_hours},
  "schedule": [
    {{
      "day": 1,
      "date": "2025-10-11",
      "topics": [
        {{
          "time": "9:00 AM - 10:00 AM",
          "topic": "Introduction to Topic",
          "description": "Cover basics",
          "type": "theory",
          "music": "lofi"
        }}
      ],
      "goals": ["Master concept 1", "Practice problem set", "Review notes"]
    }}
  ],
  "cheatSheets": [
    {{
      "title": "Quick Reference - Key Formulas",
      "content": "Formula 1: description\\nFormula 2: description",
      "type": "formulas"
    }}
  ]
}}

RULES:
1. Extract 8-15 key topics from the content
2. Create {max(3, min(14, (datetime.strptime(exam_date, '%Y-%m-%d') - datetime.now()).days))} days of schedule
3. Each day: {daily_hours} total hours split across topics
4. Use times like "9:00 AM - 10:00 AM"
5. types: "theory", "practice", "review"
6. music: "lofi", "classical", "nature", "instrumental", "focus"
7. 3-5 goals per day
8. 3-5 cheat sheets
9. NO markdown, NO code blocks, ONLY JSON

Start with {{ now:"""

        # Call Together AI (stable model and settings for JSON fidelity)
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                temperature=0.3
            )
        except Exception as ai_error:
            return jsonify({"error": f"AI model error: {str(ai_error)}"}), 500
        
        schedule_json_str = response.choices[0].message.content.strip()
        
        print(f"\n{'='*60}")
        print("📅 SCHEDULE GENERATION DEBUG")
        print(f"Response length: {len(schedule_json_str)} characters")
        print(f"First 200 chars: {schedule_json_str[:200]}")
        print(f"{'='*60}\n")

        # Robust JSON extraction using helper (handles code fences and trailing commas)
        schedule_data = extract_json_object(schedule_json_str)
        
        if not schedule_data:
            # Try one more aggressive cleanup
            try:
                # Remove ALL markdown artifacts
                cleaned = re.sub(r'```[a-z]*\n?', '', schedule_json_str)
                cleaned = re.sub(r'\n```', '', cleaned)
                cleaned = cleaned.strip()
                
                # Try to find JSON bounds more aggressively
                start = cleaned.find('{')
                end = cleaned.rfind('}')
                
                if start != -1 and end != -1:
                    json_str = cleaned[start:end+1]
                    # Fix common JSON issues
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
                    json_str = re.sub(r'}\s*{', '},{', json_str)  # Fix missing commas between objects
                    schedule_data = json.loads(json_str)
            except Exception as parse_error:
                print(f"❌ JSON parse failed: {str(parse_error)}")
                
                # FALLBACK: Generate a basic default schedule
                print("⚠️ Using fallback schedule generation...")
                
                try:
                    exam_dt = datetime.strptime(exam_date, '%Y-%m-%d')
                    days_until_exam = max(3, min(14, (exam_dt - datetime.now()).days))
                    
                    # Create simple fallback schedule
                    fallback_schedule = {
                        "title": "AI Study Plan (Fallback Mode)",
                        "totalTopics": 10,
                        "examDate": exam_date,
                        "dailyHours": daily_hours,
                        "schedule": [],
                        "cheatSheets": [
                            {
                                "title": "Quick Reference - Key Concepts",
                                "content": "Review your document for key formulas and definitions",
                                "type": "general"
                            }
                        ]
                    }
                    
                    # Generate simple daily schedule
                    start_date = datetime.now()
                    for i in range(min(days_until_exam, 7)):
                        day_date = start_date + timedelta(days=i)
                        fallback_schedule["schedule"].append({
                            "day": i + 1,
                            "date": day_date.strftime('%Y-%m-%d'),
                            "topics": [
                                {
                                    "time": "9:00 AM - 10:00 AM",
                                    "topic": f"Study Session {i+1}",
                                    "description": "Review key concepts from your materials",
                                    "type": "theory" if i < 3 else "review",
                                    "music": "lofi"
                                }
                            ],
                            "goals": [
                                "Review main concepts",
                                "Practice problems",
                                "Take notes"
                            ]
                        })
                    
                    print("✅ Fallback schedule generated")
                    return jsonify(fallback_schedule)
                    
                except Exception as fallback_error:
                    print(f"❌ Fallback also failed: {str(fallback_error)}")
                    return jsonify({
                        "error": "Failed to parse AI response as JSON",
                        "details": str(parse_error),
                        "raw_response": schedule_json_str[:1000],
                        "hint": "AI returned malformed JSON. Try again or reduce content size."
                    }), 500
        
        # Validate required fields
        if not schedule_data or 'schedule' not in schedule_data:
            return jsonify({
                "error": "Invalid schedule data structure",
                "details": "Missing 'schedule' field in response",
                "received_keys": list(schedule_data.keys()) if isinstance(schedule_data, dict) else "Not a dict",
                "raw_response": schedule_json_str[:800]
            }), 500
        
        print(f"✅ Successfully generated schedule with {len(schedule_data.get('schedule', []))} days")
        
        return jsonify(schedule_data)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error: {str(e)}")
        return jsonify({
            "error": "AI returned invalid JSON format",
            "details": str(e),
            "raw_response": schedule_json_str[:800] if 'schedule_json_str' in locals() else "No response captured",
            "hint": "The AI model failed to generate proper JSON. Try uploading a smaller document or try again."
        }), 500
    except Exception as e:
        print(f"❌ Schedule Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Schedule generation failed: {str(e)}",
            "type": type(e).__name__
        }), 500

@app.route('/api/schedule', methods=['POST'])
def schedule_api():
    """Alias route used by frontend to generate schedules (same as /api/generate-schedule)."""
    return generate_schedule()

# Add these routes to your app.py file

@app.route('/podcast')
def podcast():
    """Podcast mode page route"""
    return render_template('podcast.html')

@app.route('/api/generate-podcast-script', methods=['POST'])
def generate_podcast_script():
    """Generate AI-powered podcast script from document content"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract parameters
        summary_text = data.get('summaryText', '')
        source_text = data.get('sourceText', '')
        duration = data.get('duration', 5)  # default 5 minutes; supported: 3, 5, 10
        style = data.get('style', 'educational')
        pace = data.get('pace', 'normal')
        tone = data.get('tone', 'calm')
        language = data.get('language', 'en')
        
        if not summary_text and not source_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Build context (limit size to avoid token overflow)
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text[:2000]}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text[:2000]}\n\n"
        
        # Calculate word count target
        target_words = duration * 150
        
        # AI prompt - EMPHASIZE plain text output
        system_prompt = (
            "You are an expert podcast scriptwriter. "
            "Output ONLY the spoken script - NO JSON, NO metadata, NO code blocks. "
            "Just write the actual words that will be spoken in the podcast."
        )
        
        user_prompt = f"""Create a {duration}-minute podcast script about this content:

{context}

Requirements:
- Target length: {target_words} words
- Style: {style}
- Tone: {tone}
- Pace: {pace}

Write ONLY the podcast script (plain text). Start directly with the introduction.
If conversational style, use:
HOST A: [text]
HOST B: [text]

For single narrator, just write naturally without labels.

Begin the script now:"""

        # Token budget scaled for ~150 words/min
        max_tokens_map = {3: 900, 5: 1500, 10: 2500}
        
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens_map.get(duration, 3000),
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        
        # Clean up any JSON/markdown formatting if AI ignored instructions
        if script.startswith('{') or script.startswith('['):
            try:
                parsed = json.loads(script)
                if isinstance(parsed, dict):
                    script = parsed.get('script') or parsed.get('content') or str(parsed)
            except:
                pass
        
        # Remove code blocks
        script = re.sub(r'^```(json|text)?\s*', '', script, flags=re.IGNORECASE)
        script = re.sub(r'\s*```$', '', script)
        script = script.strip()
        
        # If still looks like JSON, extract the value
        if script.startswith('"') and script.endswith('"'):
            script = script[1:-1]
        
        # Calculate stats
        word_count = len(script.split())
        estimated_duration = round(word_count / 150, 1)
        
        return jsonify({
            "script": script,
            "wordCount": word_count,
            "estimatedDuration": estimated_duration,
            "settings": {
                "duration": duration,
                "style": style,
                "pace": pace,
                "tone": tone,
                "language": language
            }
        })
    except Exception as e:
        print(f"Podcast error: {str(e)}")
        return jsonify({"error": f"Podcast script generation failed: {str(e)}"}), 500

from elevenlabs import ElevenLabs

# Initialize ElevenLabs client
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
@app.route('/api/download-flashcards', methods=['POST'])
def download_flashcards():
    """Generate and download flashcards as a beautifully formatted PDF"""
    try:
        data = request.get_json(silent=True) or {}
        flashcards = data.get('flashcards', [])
        title = data.get('title', 'Study Flashcards')
        
        if not flashcards:
            return jsonify({"error": "No flashcards provided"}), 400
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            topMargin=0.75*inch, 
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch, 
            rightMargin=0.75*inch
        )
        
        from reportlab.lib.colors import HexColor, black, whitesmoke
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus import Table, TableStyle, PageBreak
        
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'FlashcardTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Card number style
        card_num_style = ParagraphStyle(
            'CardNumber',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#6b7280'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        # Question style
        question_style = ParagraphStyle(
            'Question',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#1f2937'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Answer style
        answer_style = ParagraphStyle(
            'Answer',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            spaceAfter=20,
            fontName='Helvetica',
            textColor=HexColor('#374151')
        )
        
        # Category/hint style
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#9ca3af'),
            spaceAfter=6,
            fontName='Helvetica-Oblique'
        )
        
        # Helper function
        def clean_text(text):
            from xml.sax.saxutils import escape as xml_escape
            text = xml_escape(str(text))
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
            return text
        
        # Build PDF content
        story = []
        
        # Title page
        story.append(Paragraph(clean_text(title), title_style))
        story.append(Paragraph(f"Total Flashcards: {len(flashcards)}", meta_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Group by category for better organization
        from collections import defaultdict
        cards_by_category = defaultdict(list)
        for card in flashcards:
            category = card.get('category', 'General')
            cards_by_category[category].append(card)
        
        # Generate flashcards
        for category, cards in cards_by_category.items():
            # Category header
            category_style = ParagraphStyle(
                'Category',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=HexColor('#2563eb'),
                spaceAfter=16,
                spaceBefore=24,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(f"📚 {clean_text(category)}", category_style))
            story.append(Spacer(1, 0.2*inch))
            
            for card in cards:
                # Card number and difficulty
                card_id = card.get('id', '?')
                difficulty = card.get('difficulty', 'medium')
                difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}.get(difficulty, '⚪')
                
                story.append(Paragraph(
                    f"Card #{card_id} {difficulty_emoji} {difficulty.capitalize()}", 
                    card_num_style
                ))
                
                # Question (with box)
                question = card.get('question', 'No question')
                story.append(Paragraph(f"<b>Q:</b> {clean_text(question)}", question_style))
                
                # Hint (if exists)
                hint = card.get('hint', '').strip()
                if hint:
                    story.append(Paragraph(f"💡 Hint: {clean_text(hint)}", meta_style))
                    story.append(Spacer(1, 0.1*inch))
                
                # Answer (with subtle background)
                answer = card.get('answer', 'No answer')
                
                # Create a simple table for the answer box
                answer_para = Paragraph(f"<b>A:</b> {clean_text(answer)}", answer_style)
                answer_table = Table([[answer_para]], colWidths=[6.5*inch])
                answer_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f3f4f6')),
                    ('PADDING', (0, 0), (-1, -1), 12),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 15),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ]))
                story.append(answer_table)
                
                # Separator
                story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f'{safe_title}_Flashcards.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Flashcard PDF generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Flashcard PDF generation failed: {str(e)}"}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert podcast script to audio - FAST version"""
    import time
    start_time = time.time()
    
    try:
        data = request.get_json(silent=True) or {}
        script = data.get('script', '')
        voice_id = data.get('voiceId', '21m00Tcm4TlvDq8ikWAM')
        
        if not script:
            return jsonify({"error": "No script provided"}), 400

        print(f"\n{'='*50}")
        print(f"🎙️ TTS REQUEST RECEIVED")
        print(f"Script length: {len(script)} characters")
        print(f"Timestamp: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*50}\n")

        # Ensure directory exists
        os.makedirs("static/audio", exist_ok=True)
        
        # Generate filename immediately
        filename = f"podcast_gtts_{int(datetime.now().timestamp())}.mp3"
        filepath = os.path.join("static/audio", filename)
        
        # Use gTTS directly (it's faster and more reliable than ElevenLabs for testing)
        print("🔊 Generating audio with gTTS...")
        
        try:
            # Generate the audio file
            tts = gTTS(text=script, lang='en', slow=False)
            tts.save(filepath)
            
            generation_time = time.time() - start_time
            print(f"✅ Audio generated in {generation_time:.2f} seconds")
            print(f"📁 File saved: {filepath}")
            print(f"📊 File size: {os.path.getsize(filepath) / 1024:.1f} KB")
            
            audio_url = f"/static/audio/{filename}"
            
            print(f"🌐 Audio URL: {audio_url}")
            print(f"{'='*50}\n")
            
            return jsonify({
                "message": "Audio generated successfully",
                "audioUrl": audio_url,
                "filename": filename,
                "generationTime": round(generation_time, 2),
                "voiceId": "gtts",
                "model": "gtts"
            })
            
        except Exception as gtts_error:
            print(f"❌ gTTS Error: {str(gtts_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"Audio generation failed: {str(gtts_error)}"
            }), 500

    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"TTS failed: {str(e)}"}), 500


@app.route('/api/save-podcast', methods=['POST'])
def save_podcast():
    """Save podcast metadata for later retrieval"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract podcast data
        podcast_data = {
            'title': data.get('title', 'Untitled Podcast'),
            'script': data.get('script', ''),
            'settings': data.get('settings', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        # In production, save to database
        # For now, just return success
        return jsonify({
            "success": True,
            "message": "Podcast saved successfully",
            "podcastId": f"podcast_{int(datetime.now().timestamp())}"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to save podcast: {str(e)}"}), 500
@app.route('/api/download-cheatsheet', methods=['POST'])
def download_cheatsheet():
    """Generate and download a cheat sheet PDF with improved formatting"""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'Study Cheat Sheet')
        content = data.get('content', '')
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        # Create PDF in memory with better margins
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              topMargin=0.75*inch, bottomMargin=0.75*inch,
                              leftMargin=0.75*inch, rightMargin=0.75*inch)
        
        # Import required classes
        from reportlab.lib.colors import black, darkblue, darkgreen
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
        
        styles = getSampleStyleSheet()
        
        # Enhanced title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=black,
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Heading style for sections
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=black,
            spaceAfter=12,
            spaceBefore=16,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        # Body text style
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            spaceAfter=8,
            spaceBefore=4,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            textColor=black
        )
        
        # List style for bullet points
        list_style = ParagraphStyle(
            'CustomList',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
            spaceBefore=2,
            leftIndent=20,
            bulletIndent=10,
            fontName='Helvetica',
            textColor=black
        )
        
        # Build PDF content
        story = []
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Process content with better formatting
        sections = content.split('\n\n')
        for section in sections:
            if section.strip():
                # Handle different content types
                lines = section.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Handle headers (## or **bold text**:)
                    if line.startswith('##') or (line.startswith('**') and line.endswith(':**')):
                        header_text = line.replace('##', '').replace('**', '').replace(':', '').strip()
                        story.append(Paragraph(header_text, heading_style))
                    
                    # Handle bullet points
                    elif line.startswith('- ') or line.startswith('• '):
                        bullet_text = line[2:].strip()
                        # Clean up markdown formatting
                        bullet_text = bullet_text.replace('**', '<b>').replace('**', '</b>')
                        bullet_text = bullet_text.replace('*', '<i>').replace('*', '</i>')
                        story.append(Paragraph(f'• {bullet_text}', list_style))
                    
                    # Handle numbered lists
                    elif line.split('.')[0].strip().isdigit():
                        story.append(Paragraph(line, list_style))
                    
                    # Handle regular paragraphs
                    else:
                        # Clean up markdown formatting
                        line = line.replace('**', '<b>').replace('**', '</b>')
                        line = line.replace('*', '<i>').replace('*', '</i>')
                        story.append(Paragraph(line, body_style))
                
                story.append(Spacer(1, 0.15*inch))
        
        # Build PDF with proper error handling
        try:
            doc.build(story)
        except Exception as build_error:
            print(f"PDF build error: {str(build_error)}")
            return jsonify({"error": f"PDF generation failed: {str(build_error)}"}), 500
            
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{title.replace(" ", "_").replace("/", "_")}.pdf'
        )
        
    except Exception as e:
        print(f"Cheat sheet generation error: {str(e)}")
        import traceback
        traceback.print_exc()
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
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3500,
            temperature=0.6
        )
        print(response.choices[0].message.content)


        
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
            model="openai/gpt-oss-120b",
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

import re
from flask import request, jsonify

def clean_response(text):
    """Remove markdown formatting and clean up response text"""
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Remove headers
    text = re.sub(r'#{1,6}\s+', '', text)
    
    # Remove bullet points/lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


import re
from flask import request, jsonify

def clean_response(text):
    """Remove markdown formatting and clean up response text"""
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Remove headers
    text = re.sub(r'#{1,6}\s+', '', text)
    
    # Remove bullet points/lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    context_text = (data.get('summary_text') or '').strip()
    source_text = (data.get('source_text') or '').strip()
    mode = (data.get('mode') or 'professor').strip()

    if not question:
        return jsonify({"error": "Missing 'question'"}), 400

    # Build concise system prompt
    system_prompt = (
        "You are an expert professor who explains concepts clearly and concisely.\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "- Keep responses SHORT: 2-3 sentences for simple questions, max 1 short paragraph for complex ones\n"
        "- Use PLAIN TEXT ONLY - absolutely NO markdown formatting (no **, __, ##, bullets, or numbered lists)\n"
        "- Write in natural prose using normal sentences\n"
        "- Start with the direct answer immediately\n"
        "- Be precise and avoid unnecessary elaboration\n"
        "- If the answer is not in the context, simply state: 'This information is not available in the provided document.'\n\n"
        "Answer the question directly using plain language."
    ) if mode == 'professor' else (
        "You are a helpful assistant. Keep responses very concise (2-3 sentences) and use plain text only - no markdown formatting."
    )

    # Build user prompt with context
    user_prompt = f"Context:\n{source_text[:2000] if source_text else context_text[:1000]}\n\nQuestion: {question}"

    try:
        # Call the LLM API
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,  # Limit response length
            temperature=0.4
        )
        
        # Extract the AI response
        ai_response = response.choices[0].message.content if response and response.choices else ""
        
        # Clean the response to remove any markdown
        cleaned_answer = clean_response(ai_response)
        
        # Optionally truncate if still too long
        if len(cleaned_answer) > 500:
            cleaned_answer = cleaned_answer[:497] + "..."
        
        return jsonify({
            "response": cleaned_answer,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error generating response: {str(e)}",
            "status": "error"
        }), 500
    

@app.route('/cheatsheet')
def cheatsheet():
    """Ultimate Cheat Sheet page route"""
    return render_template('cheatsheet.html')


@app.route('/api/generate-ultimate-cheatsheet', methods=['POST'])
def generate_ultimate_cheatsheet():
    """Generate comprehensive, structured cheat sheet with customizable detail"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract parameters (JSON path)
        summary_text = data.get('summaryText', '') if isinstance(data, dict) else ''
        source_text = data.get('sourceText', '') if isinstance(data, dict) else ''
        detail_level = data.get('detailLevel', 5)  # 1-10 scale
        page_count = data.get('pageCount', 3)  # Target pages
        include_sections = data.get('includeSections', {
            'keyTopics': True,
            'definitions': True,
            'formulas': True,
            'examples': True,
            'qa': True,
            'quickTips': True,
            'mnemonics': True,
            'commonMistakes': True
        })
        
        if not summary_text and not source_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Build context
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
        
        # Calculate content density based on detail level and page count
        # Rough estimate: 500 words per page at normal density
        target_words = page_count * 500 * (detail_level / 5)
        
        # Detail level descriptions
        detail_descriptions = {
            1: "Ultra-concise, only absolute essentials",
            2: "Very brief, key points only",
            3: "Concise, important concepts",
            4: "Balanced, good coverage",
            5: "Detailed, comprehensive",
            6: "Very detailed, thorough explanations",
            7: "Extensive, includes nuances",
            8: "Deep dive, rich examples",
            9: "Exhaustive, expert-level",
            10: "Complete mastery guide"
        }
        
        # Build dynamic section instructions
        section_specs = []
        
        if include_sections.get('keyTopics'):
            topics_count = max(8, min(40, int(page_count * 3 * (detail_level / 5))))
            section_specs.append(
                f"**📚 Key Topics & Concepts** ({topics_count} bullets)\n"
                f"- Organize main concepts hierarchically\n"
                f"- Each point: topic + brief explanation{'+ example' if detail_level >= 5 else ''}\n"
                f"- Use sub-bullets for related subtopics\n"
            )
        
        if include_sections.get('definitions'):
            def_count = max(5, min(25, int(page_count * 2 * (detail_level / 5))))
            section_specs.append(
                f"**📖 Essential Definitions** ({def_count} terms)\n"
                f"- Format: **Term**: Clear, precise definition\n"
                f"- {('Include usage context' if detail_level >= 5 else 'Brief definitions only')}\n"
            )
        
        if include_sections.get('formulas'):
            formula_count = max(3, min(15, int(page_count * 1.5 * (detail_level / 5))))
            section_specs.append(
                f"**🧮 Key Formulas & Equations** ({formula_count} formulas)\n"
                f"- Show formula + what each variable means\n"
                f"- {('Include when to use it' if detail_level >= 5 else 'Formula only')}\n"
            )
        
        if include_sections.get('examples'):
            example_count = max(3, min(12, int(page_count * 1.2 * (detail_level / 5))))
            section_specs.append(
                f"**💡 Worked Examples** ({example_count} examples)\n"
                f"- Real-world or typical exam-style problems\n"
                f"- {('Show step-by-step solution' if detail_level >= 5 else 'Brief example + answer')}\n"
            )
        
        if include_sections.get('qa'):
            qa_count = max(5, min(20, int(page_count * 2 * (detail_level / 5))))
            section_specs.append(
                f"**❓ Critical Questions & Answers** ({qa_count} Q&As)\n"
                f"- High-yield questions likely to appear\n"
                f"- {('Detailed answers with reasoning' if detail_level >= 5 else 'Concise answers')}\n"
            )
        
        if include_sections.get('quickTips'):
            tips_count = max(4, min(15, int(page_count * 1.5 * (detail_level / 5))))
            section_specs.append(
                f"**⚡ Quick Tips & Shortcuts** ({tips_count} tips)\n"
                f"- Time-saving techniques\n"
                f"- Common patterns to recognize\n"
            )
        
        if include_sections.get('mnemonics'):
            section_specs.append(
                f"**🧠 Memory Aids & Mnemonics**\n"
                f"- Create memorable acronyms or phrases\n"
                f"- Visual associations for complex concepts\n"
            )
        
        if include_sections.get('commonMistakes'):
            mistake_count = max(3, min(10, int(page_count * 1 * (detail_level / 5))))
            section_specs.append(
                f"**⚠️ Common Mistakes to Avoid** ({mistake_count} pitfalls)\n"
                f"- Typical errors and why they happen\n"
                f"- How to avoid them\n"
            )
        
        sections_instruction = "\n".join(section_specs)
        
        # AI prompt
        system_prompt = (
            "You are an expert academic content creator who produces exceptional study materials. "
            "Your cheat sheets are perfectly structured, highly organized, and designed for maximum retention. "
            "Use clear Markdown formatting with excellent visual hierarchy."
        )
        
        user_prompt = f"""Create the ULTIMATE CHEAT SHEET from the following content:

CONTENT:
{context}

SPECIFICATIONS:
- Detail Level: {detail_level}/10 ({detail_descriptions.get(detail_level, 'Detailed')})
- Target Length: ~{int(target_words)} words (approximately {page_count} pages)
- Target Pages: {page_count}

REQUIRED STRUCTURE:
Create a comprehensive cheat sheet with these sections:

{sections_instruction}

FORMATTING REQUIREMENTS:
1. Start with a clear title: # [Subject] - Ultimate Cheat Sheet
2. Use Markdown headers (##, ###) for section organization
3. Use bold (**text**) for key terms and emphasis
4. Use code blocks (`) for formulas and technical terms
5. Include blank lines between sections for readability
6. Use bullet points and sub-bullets for hierarchical information
7. Use numbered lists for sequential processes or steps
8. Add horizontal rules (---) between major sections

CONTENT GUIDELINES:
- Extract and organize ALL important information from the source
- Prioritize high-yield content (likely to appear on tests)
- Be precise and accurate - no fluff or filler
- {'Include detailed explanations and examples' if detail_level >= 5 else 'Keep explanations concise'}
- {'Show step-by-step workings' if detail_level >= 6 else 'Focus on key points'}
- Group related concepts together logically
- Cross-reference related topics where helpful

QUALITY STANDARDS:
- Every bullet point must add value
- Definitions must be precise and complete
- Examples must be clear and illustrative
- Formulas must show what variables represent
- Tips must be actionable
- Zero redundancy

TARGET LENGTH: Aim for approximately {int(target_words)} words to fit {page_count} pages

Generate the complete cheat sheet now (Markdown format):"""

        # Calculate appropriate max_tokens
        max_tokens_estimate = min(8000, int(target_words * 1.5))
        
        # Call Together AI
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens_estimate,
            temperature=0.4
        )
        
        cheatsheet_content = response.choices[0].message.content.strip()
        
        # Calculate actual stats
        word_count = len(cheatsheet_content.split())
        estimated_pages = round(word_count / 500, 1)
        
        return jsonify({
            "content": cheatsheet_content,
            "stats": {
                "wordCount": word_count,
                "estimatedPages": estimated_pages,
                "detailLevel": detail_level,
                "requestedPages": page_count
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Cheat sheet generation failed: {str(e)}"}), 500


@app.route('/api/download-ultimate-cheatsheet', methods=['POST'])
def download_ultimate_cheatsheet():
    """Generate and download the ultimate cheat sheet as PDF"""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'Ultimate Cheat Sheet')
        content = data.get('content', '')
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        # Create PDF in memory with better formatting
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            topMargin=0.75*inch, 
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch, 
            rightMargin=0.75*inch
        )
        
        # Enhanced styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CheatSheetTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor='#1e40af',
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        heading2_style = ParagraphStyle(
            'CheatSheetH2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor='#2563eb',
            spaceAfter=12,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        )
        
        heading3_style = ParagraphStyle(
            'CheatSheetH3',
            parent=styles['Heading3'],
            fontSize=13,
            textColor='#3b82f6',
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CheatSheetBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        bullet_style = ParagraphStyle(
            'CheatSheetBullet',
            parent=styles['BodyText'],
            fontSize=10,
            leading=13,
            spaceAfter=4,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        # Build PDF content
        story = []
        
        # Helpers for safe inline formatting
        import re
        from xml.sax.saxutils import escape as xml_escape

        def clean_inline(text: str) -> str:
            # Escape HTML entities first
            text = xml_escape(text)
            # Bold: **text** -> <b>text</b>
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            # Inline code: `code` -> <font face="Courier">code</font>
            text = re.sub(r"`([^`]+)`", r"<font face=\"Courier\">\1</font>", text)
            return text

        # Parse markdown-like content
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 0.1*inch))
                continue
            
            # Headers
            if line.startswith('# '):
                text = clean_inline(line[2:].strip())
                story.append(Paragraph(text, title_style))
            elif line.startswith('## '):
                text = clean_inline(line[3:].strip())
                story.append(Paragraph(text, heading2_style))
            elif line.startswith('### '):
                text = clean_inline(line[4:].strip())
                story.append(Paragraph(text, heading3_style))
            # Bullets
            elif line.startswith('- ') or line.startswith('* '):
                text = clean_inline(line[2:].strip())
                story.append(Paragraph(f"• {text}", bullet_style))
            # Numbered lists
            elif len(line) > 2 and line[0].isdigit() and line[1:3] in ['. ', ') ']:
                # Keep the original index, clean the rest
                try:
                    idx_end = line.index(' ')
                except ValueError:
                    idx_end = 2
                prefix = xml_escape(line[:idx_end])
                text = clean_inline(line[idx_end+1:].strip())
                story.append(Paragraph(f"{prefix} {text}", bullet_style))
            # Horizontal rules
            elif line.startswith('---'):
                story.append(Spacer(1, 0.15*inch))
            # Regular paragraphs
            else:
                text = clean_inline(line)
                story.append(Paragraph(text, body_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f'{safe_title}_CheatSheet.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import time

# Add this route to your app.py

@app.route('/research')
def research():
    """Research paper generator page"""
    return render_template('research.html')


@app.route('/api/web-research', methods=['POST'])
def web_research():
    """Perform intelligent web research on a topic"""
    try:
        data = request.get_json(silent=True) or {}
        query = data.get('query', '').strip()
        depth = data.get('depth', 5)  # Number of sources to fetch
        
        if not query:
            return jsonify({"error": "No search query provided"}), 400
        
        print(f"\n🔍 Starting web research for: {query}")
        
        # Use DuckDuckGo search (no API key needed)
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract search results
            results = []
            result_divs = soup.find_all('div', class_='result')[:depth]
            
            for div in result_divs:
                title_elem = div.find('a', class_='result__a')
                snippet_elem = div.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    url = title_elem.get('href', '')
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True)
                    
                    # Determine source credibility
                    domain = urlparse(url).netloc
                    credibility = 'high' if any(x in domain for x in ['.edu', '.gov', '.org']) else 'medium'
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'domain': domain,
                        'credibility': credibility
                    })
            
            print(f"✅ Found {len(results)} web sources")
            return jsonify({
                'results': results,
                'query': query,
                'count': len(results)
            })
            
        except Exception as search_error:
            print(f"⚠️ Web search failed: {str(search_error)}")
            return jsonify({
                'results': [],
                'query': query,
                'count': 0,
                'warning': 'Web search unavailable, using PDF content only'
            })
            
    except Exception as e:
        return jsonify({"error": f"Web research failed: {str(e)}"}), 500

# Updated generate_research_paper function with better model and token limits

@app.route('/api/generate-research-paper', methods=['POST'])
def generate_research_paper():
    """Generate comprehensive research paper with web intelligence"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Extract parameters
        topic = data.get('topic', '').strip()
        description = data.get('description', '').strip()
        revolves_around = data.get('revolvesAround', '').strip()
        how_it_works = data.get('howItWorks', '').strip()
        related_topics = data.get('relatedTopics', '').strip()
        pdf_content = data.get('pdfContent', '').strip()
        web_sources = data.get('webSources', [])
        depth_level = data.get('depthLevel', 'detailed')  # quick, detailed, comprehensive
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Build comprehensive context
        context_parts = []
        
        if description:
            context_parts.append(f"TOPIC DESCRIPTION:\n{description}\n")
        
        if revolves_around:
            context_parts.append(f"KEY FOCUS AREAS:\n{revolves_around}\n")
        
        if how_it_works:
            context_parts.append(f"MECHANISM/PROCESS:\n{how_it_works}\n")
        
        if related_topics:
            context_parts.append(f"RELATED TOPICS:\n{related_topics}\n")
        
        if pdf_content:
            context_parts.append(f"UPLOADED DOCUMENT CONTENT:\n{pdf_content[:4000]}\n")
        
        if web_sources:
            web_context = "WEB RESEARCH FINDINGS:\n"
            for i, source in enumerate(web_sources[:10], 1):
                web_context += f"\n[Source {i}] {source.get('title', 'Unknown')}\n"
                web_context += f"URL: {source.get('url', 'N/A')}\n"
                web_context += f"Summary: {source.get('snippet', 'N/A')}\n"
            context_parts.append(web_context)
        
        full_context = "\n".join(context_parts)
        
        # UPDATED: Much higher token limits for detailed research papers
        depth_configs = {
            'quick': {
                'label': 'Quick Overview',
                'word_target': 2000,
                'max_tokens': 3000,  # Increased from 2500
                'detail': 'concise overview with key points',
                'sections': 'Abstract, Introduction, Main Discussion (3-4 sections), Conclusion, Key References'
            },
            'detailed': {
                'label': 'Detailed Analysis',
                'word_target': 5000,
                'max_tokens': 7000,  # Increased from 5000
                'detail': 'comprehensive analysis with examples and explanations',
                'sections': 'Abstract, Introduction, Literature Review, Detailed Analysis (5-7 sections), Case Studies, Discussion, Conclusion, References, Further Reading'
            },
            'comprehensive': {
                'label': 'Comprehensive Research',
                'word_target': 8000,
                'max_tokens': 12000,  # Increased from 7500
                'detail': 'exhaustive research with deep analysis, multiple perspectives, and extensive examples',
                'sections': 'Abstract, Introduction, Background, Literature Review, Theoretical Framework, Detailed Analysis (8-10 sections), Methodology, Case Studies, Comparative Analysis, Applications, Challenges & Solutions, Future Directions, Conclusion, References, Appendices, Recommended Resources'
            }
        }
        
        config = depth_configs.get(depth_level, depth_configs['detailed'])
        
        # System prompt remains the same
        system_prompt = """You are an expert academic researcher and technical writer with PhDs in multiple fields. 

Your research papers are known for:
- Exceptional depth and clarity
- Rigorous academic standards
- Comprehensive coverage of all aspects
- Clear explanations of complex concepts
- Well-structured logical flow
- Proper citations and references
- Balanced perspectives
- Practical applications and examples

Write in an authoritative yet accessible academic style. Use proper Markdown formatting for structure."""

        # User prompt (keeping your existing detailed prompt)
        user_prompt = f"""Generate a {config['label']} research paper on the following topic.

TOPIC: {topic}

RESEARCH CONTEXT:
{full_context}

PAPER SPECIFICATIONS:
- Target Length: ~{config['word_target']} words
- Detail Level: {config['detail']}
- Required Sections: {config['sections']}

STRUCTURE REQUIREMENTS:

# {topic}
*A Comprehensive Research Analysis*

---

## Abstract
- 150-250 word summary
- Key findings and contributions
- Research scope and methodology

## 1. Introduction
- Clear problem statement
- Research significance and motivation
- Objectives and scope
- Paper organization overview

## 2. Background & Context
- Historical development
- Current state of the field
- Key terminology and definitions
- Fundamental concepts

## 3. Literature Review
- Existing research and theories
- Major contributions and milestones
- Gaps in current knowledge
- Theoretical frameworks

## 4. Detailed Analysis

### 4.1 [First Major Aspect]
- In-depth exploration
- Technical details
- Supporting evidence
- Real-world examples

### 4.2 [Second Major Aspect]
- Comprehensive coverage
- Mechanisms and processes
- Data and findings
- Case studies

### 4.3 [Third Major Aspect]
- Critical analysis
- Comparative perspectives
- Strengths and limitations
- Implications

[Continue with 4.4, 4.5, etc. as needed based on topic complexity]

## 5. Methodology & Approaches
- Research methods used
- Data collection and analysis
- Experimental setups (if applicable)
- Validation techniques

## 6. Applications & Use Cases
- Practical applications
- Industry implementations
- Real-world scenarios
- Success stories and examples

## 7. Challenges & Limitations
- Current obstacles
- Technical limitations
- Ethical considerations
- Areas of debate

## 8. Future Directions
- Emerging trends
- Research opportunities
- Potential developments
- Long-term outlook

## 9. Discussion
- Synthesis of findings
- Critical evaluation
- Broader implications
- Connections to related fields

## 10. Conclusion
- Summary of key points
- Main contributions
- Final insights
- Recommendations

## References
[Cite all web sources provided, format as: Author/Source, Title, URL]

## Further Reading & Resources
### Academic Papers
- Key papers in the field

### Books & Guides
- Recommended textbooks

### Online Resources
- Tutorials and courses
- Documentation
- Community resources

### Video Content
- Educational videos
- Lectures and talks
- Demonstrations

---

WRITING GUIDELINES:

1. **Depth & Detail**
   - Explain concepts thoroughly, don't assume knowledge
   - Include specific examples and concrete details
   - Provide context for technical terms
   - Use analogies where helpful

2. **Structure & Flow**
   - Use clear headers and subheaders (##, ###)
   - Create logical transitions between sections
   - Build concepts progressively
   - Reference earlier sections when connecting ideas

3. **Academic Rigor**
   - Make evidence-based statements
   - Cite sources properly
   - Present multiple perspectives when relevant
   - Acknowledge limitations and uncertainties

4. **Clarity & Accessibility**
   - Define technical terms on first use
   - Use clear, concise sentences
   - Break down complex ideas step-by-step
   - Include illustrative examples

5. **Formatting**
   - Use **bold** for key terms and emphasis
   - Use `code formatting` for technical terms, formulas, or code
   - Use > blockquotes for important definitions
   - Use bullet points and numbered lists appropriately
   - Include horizontal rules (---) between major sections

6. **Content Requirements**
   - Every section must add unique value
   - No repetition or filler content
   - Include specific data, numbers, examples when possible
   - Connect theory to practice

7. **Citations & References**
   - Cite web sources provided in context
   - Format: [Source Title](URL) or as footnotes
   - Prioritize credible sources (.edu, .gov, .org)
   - Include publication dates when available
Generate the complete research paper now following ALL guidelines above. Make it comprehensive, insightful, and publication-ready."""
        print(f"\n📝 Generating research paper on: {topic}")
        print(f"📊 Depth Level: {config['label']}")
        print(f"🎯 Target: ~{config['word_target']} words")
        print(f"🔢 Max Tokens: {config['max_tokens']}")
        
        # Try multiple models with graceful fallback if a model is not available
        models_to_try = [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",          # preferred (Together model ID)
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",     # common alt
            "meta-llama/Llama-3.1-70B-Instruct-Turbo",          # alias alt
            "meta-llama/Meta-Llama-3-70B-Instruct",             # older naming
            "openai/gpt-oss-20b"                                # stable fallback
        ]

        response = None
        selected_model = None
        last_error = None

        for model_id in models_to_try:
            try:
                print(f"Trying model: {model_id}")
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=config['max_tokens'],
                    temperature=0.7
                )
                selected_model = model_id
                break
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                if any(tok in err_str.lower() for tok in ["model_not_available", "model not available", "404", "not found", "invalid_request_error"]):
                    print(f"Model unavailable: {model_id} -> {err_str}")
                    continue
                print(f"Model failed: {model_id} -> {err_str}")
                continue

        if not response:
            return jsonify({"error": f"No available model from fallback list. Last error: {last_error}"}), 500

        paper_content = response.choices[0].message.content.strip()

        # Calculate stats
        word_count = len(paper_content.split())
        estimated_pages = round(word_count / 500, 1)

        print(f"Research paper generated: {word_count} words ({estimated_pages} pages)")
        if selected_model:
            print(f"Model used: {selected_model}")

        return jsonify({
            "paper": paper_content,
            "stats": {
                "wordCount": word_count,
                "estimatedPages": estimated_pages,
                "depthLevel": depth_level,
                "sourceCount": len(web_sources),
                "model": selected_model or "unknown"
            },
            "metadata": {
                "topic": topic,
                "generatedAt": datetime.now().isoformat(),
                "sourcesUsed": len(web_sources)
            }
        })
        title_style = ParagraphStyle(
            'ResearchTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1a1a1a',
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
        
        author_style = ParagraphStyle(
            'Author',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=50,
            alignment=1,
            fontName='Helvetica'
        )
        
        # Section headers
        h2_style = ParagraphStyle(
            'ResearchH2',
            parent=styles['Heading1'],
            fontSize=16,
            textColor='#2c3e50',
            spaceAfter=12,
            spaceBefore=24,
            fontName='Helvetica-Bold'
        )
        
        h3_style = ParagraphStyle(
            'ResearchH3',
            parent=styles['Heading2'],
            fontSize=13,
            textColor='#34495e',
            spaceAfter=10,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        )
        
        # Body text
        body_style = ParagraphStyle(
            'ResearchBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            alignment=4,  # Justify
            fontName='Times-Roman'
        )
        
        bullet_style = ParagraphStyle(
            'ResearchBullet',
            parent=styles['BodyText'],
            fontSize=11,
            leading=15,
            spaceAfter=6,
            leftIndent=30,
            fontName='Times-Roman'
        )
        
        # Helper function for safe text processing
        def clean_inline(text: str) -> str:
            from xml.sax.saxutils import escape as xml_escape
            text = xml_escape(text)
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
            text = re.sub(r"\[(.*?)\]\((.*?)\)", r"<u>\1</u>", text)  # Links become underlined
            return text
        
        # Build PDF
        story = []
        
        # Title page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(clean_inline(title), title_style))
        story.append(Paragraph(author, author_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", author_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Process content
        lines = content.split('\n')
        in_code_block = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 0.15*inch))
                continue
            
            # Code blocks
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                story.append(Paragraph(f"<font face='Courier' size='9'>{xml_escape(line)}</font>", body_style))
                continue
            
            # Headers
            if line.startswith('# '):
                text = clean_inline(line[2:].strip())
                story.append(Paragraph(text, title_style))
            elif line.startswith('## '):
                text = clean_inline(line[3:].strip())
                story.append(Paragraph(text, h2_style))
            elif line.startswith('### '):
                text = clean_inline(line[4:].strip())
                story.append(Paragraph(text, h3_style))
            # Bullets
            elif line.startswith('- ') or line.startswith('* '):
                text = clean_inline(line[2:].strip())
                story.append(Paragraph(f"• {text}", bullet_style))
            # Numbered lists
            elif len(line) > 2 and line[0].isdigit() and line[1:3] in ['. ', ') ']:
                text = clean_inline(line[2:].strip())
                story.append(Paragraph(f"{line[0]}. {text}", bullet_style))
            # Horizontal rules
            elif line.startswith('---'):
                story.append(Spacer(1, 0.2*inch))
            # Blockquotes
            elif line.startswith('> '):
                text = clean_inline(line[2:].strip())
                quote_style = ParagraphStyle(
                    'Quote',
                    parent=body_style,
                    leftIndent=40,
                    rightIndent=40,
                    textColor='#555555',
                    fontSize=10
                )
                story.append(Paragraph(f"<i>{text}</i>", quote_style))
            # Regular paragraphs
            else:
                text = clean_inline(line)
                story.append(Paragraph(text, body_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f'{safe_title}_Research_Paper.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


if __name__ == "__main__":
    # Start the Flask development server when running this file directly
    # Example: Running will print the link like: http://127.0.0.1:5000
    port = int(os.getenv("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)