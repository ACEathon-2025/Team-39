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


app = Flask(__name__)
load_dotenv()

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


@app.route('/')
def index():
    return render_template('v3.html')


@app.route('/time')
def time():
    return render_template('time.html')


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

        # Call Together AI (stable model and settings for JSON fidelity)
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2500,
            temperature=0.3
        )
        
        schedule_json_str = response.choices[0].message.content.strip()

        # Robust JSON extraction using helper (handles code fences and trailing commas)
        schedule_data = extract_json_object(schedule_json_str)
        if not schedule_data or 'schedule' not in schedule_data:
            return jsonify({
                "error": "Failed to parse AI response as JSON",
                "raw_response": schedule_json_str[:800]
            }), 500
        
        return jsonify(schedule_data)
        
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Failed to parse AI response as JSON",
            "details": str(e),
            "raw_response": schedule_json_str[:500] if 'schedule_json_str' in locals() else ""
        }), 500
    except Exception as e:
        return jsonify({"error": f"Schedule generation failed: {str(e)}"}), 500

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
        duration = data.get('duration', 10)  # 10, 30, or 60 minutes
        style = data.get('style', 'educational')  # educational, conversational, interview, storytelling
        pace = data.get('pace', 'normal')  # slow, normal, fast
        tone = data.get('tone', 'calm')  # enthusiastic, calm, serious, friendly
        language = data.get('language', 'en')  # en, es, fr, de, hi
        
        if not summary_text and not source_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Build context
        context = ""
        if summary_text:
            context += f"DOCUMENT SUMMARY:\n{summary_text}\n\n"
        if source_text:
            context += f"FULL DOCUMENT TEXT:\n{source_text}\n\n"
        
        # Style-specific instructions
        style_instructions = {
            'educational': {
                'format': 'Single narrator explaining concepts clearly with examples',
                'structure': 'Introduction → Main concepts → Key takeaways → Conclusion',
                'voice': 'Professional, authoritative, teaching tone'
            },
            'conversational': {
                'format': 'Two hosts discussing the topic in a natural, engaging dialogue',
                'structure': 'Host A introduces → Both discuss main points → Back-and-forth Q&A → Wrap-up',
                'voice': 'Friendly, casual, occasionally humorous'
            },
            'interview': {
                'format': 'Interviewer asking questions, expert answering',
                'structure': 'Introduction → Series of insightful questions and answers → Final thoughts',
                'voice': 'Curious interviewer, knowledgeable expert'
            },
            'storytelling': {
                'format': 'Narrative-driven explanation with story elements',
                'structure': 'Hook/scenario → Journey through concepts → Resolution/insights',
                'voice': 'Engaging, descriptive, narrative flow'
            }
        }
        
        # Pace adjustments
        pace_instructions = {
            'slow': 'Take time to explain concepts thoroughly with multiple examples. Use longer pauses.',
            'normal': 'Balanced pace with clear explanations and relevant examples.',
            'fast': 'Brisk pace focusing on key points and essential information. Quick transitions.'
        }
        
        # Tone adjustments
        tone_instructions = {
            'enthusiastic': 'High energy, excited about the topic, use exclamations and positive language',
            'calm': 'Measured, soothing delivery, professional and composed',
            'serious': 'Formal, authoritative, focused on facts and accuracy',
            'friendly': 'Warm, approachable, conversational and relatable'
        }
        
        # Language settings
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'hi': 'Hindi'
        }
        
        selected_style = style_instructions.get(style, style_instructions['educational'])
        
        # Calculate word count target (average speaking rate: 150 words per minute)
        target_words = duration * 150
        
        # AI prompt for podcast script generation
        system_prompt = (
            "You are an expert podcast scriptwriter who creates engaging, well-structured audio content. "
            "Create scripts that sound natural when spoken aloud. Use conversational language. "
            "Output ONLY the script text, no JSON, no metadata."
        )
        
        user_prompt = f"""Create a {duration}-minute podcast script from the following content:

CONTENT TO COVER:
{context}

PODCAST SPECIFICATIONS:
- Duration: {duration} minutes (approximately {target_words} words)
- Style: {style} - {selected_style['format']}
- Structure: {selected_style['structure']}
- Voice/Tone: {tone_instructions.get(tone, tone_instructions['calm'])}
- Pace: {pace_instructions.get(pace, pace_instructions['normal'])}
- Language: {language_names.get(language, 'English')}

SCRIPT REQUIREMENTS:

1. FORMAT FOR {style.upper()} STYLE:
   {selected_style['format']}

2. STRUCTURE:
   - Opening (10%): Engaging hook and introduction
   - Main Content (75%): Core concepts from the document
   - Closing (15%): Summary and final thoughts

3. WRITING STYLE:
   - Write for the ear, not the eye (conversational, natural flow)
   - Use short sentences and simple language
   - Include natural transitions ("Now, let's talk about...", "Here's the interesting part...")
   - Add verbal cues for emphasis ("This is crucial:", "Pay attention to this:")
   - {selected_style['voice']}

4. CONTENT GUIDELINES:
   - Extract and explain key concepts from the provided content
   - Use analogies and examples to clarify complex ideas
   - Include relevant details but prioritize clarity
   - Make connections between different concepts
   - {pace_instructions.get(pace)}

5. DIALOGUE FORMAT (if conversational/interview style):
   HOST A: [dialogue]
   HOST B: [dialogue]
   
   For single narrator, just write the script without labels.

6. LENGTH:
   Target approximately {target_words} words ({duration} minutes at normal speaking pace)

OUTPUT REQUIREMENTS:
- Write ONLY the podcast script
- No metadata, no JSON formatting
- Natural, speakable language
- Clear section breaks with [PAUSE] where appropriate
- Include [INTRO MUSIC], [OUTRO MUSIC] markers if relevant

Write the complete {language_names.get(language, 'English')} podcast script now:"""

        # Call Together AI with higher token limit for longer podcasts
        max_tokens_map = {
            10: 2500,
            30: 5000,
            60: 8000
        }
        
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
        
        # Calculate actual word count and estimated duration
        word_count = len(script.split())
        estimated_duration = round(word_count / 150, 1)  # 150 words per minute
        
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
        return jsonify({"error": f"Podcast script generation failed: {str(e)}"}), 500

from elevenlabs import ElevenLabs

# Initialize ElevenLabs client
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    """Convert podcast script to real audio using ElevenLabs TTS"""
    try:
        data = request.get_json(silent=True) or {}
        script = data.get('script', '')
        # Prefer an explicit voiceId from the client; otherwise use env default
        voice_id = data.get('voiceId') or os.getenv("ELEVENLABS_VOICE_ID")
        model = data.get('model', 'eleven_turbo_v2')  # Stable and free-tier friendly

        if not script:
            return jsonify({"error": "No script provided"}), 400

        os.makedirs("static/audio", exist_ok=True)

        try:
            if not voice_id:
                raise RuntimeError("missing_voice_id")

            # Try ElevenLabs first
            audio = eleven_client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=model,
                text=script,
                output_format="mp3_44100_128"
            )

            filename = f"podcast_{int(datetime.now().timestamp())}.mp3"
            filepath = os.path.join("static/audio", filename)
            with open(filepath, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            audio_url = f"/static/audio/{filename}"
            return jsonify({
                "message": "TTS audio generated successfully.",
                "script": script,
                "audioUrl": audio_url,
                "voiceId": voice_id,
                "model": model
            })
        except Exception as e:
            # Fallback to gTTS if ElevenLabs fails (e.g., quota_exceeded or missing voice id)
            try:
                tts = gTTS(text=script)
                filename = f"podcast_fallback_{int(datetime.now().timestamp())}.mp3"
                filepath = os.path.join("static/audio", filename)
                tts.save(filepath)
                audio_url = f"/static/audio/{filename}"
                return jsonify({
                    "message": "TTS audio generated via fallback (gTTS).",
                    "script": script,
                    "audioUrl": audio_url,
                    "voiceId": voice_id or "gtts",
                    "model": "gtts"
                })
            except Exception as ge:
                return jsonify({"error": f"TTS generation failed (fallback): {str(ge)}"}), 500

    except Exception as e:
        return jsonify({"error": f"TTS generation failed: {str(e)}"}), 500


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
            model="openai/gpt-oss-20b",
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
        "Always cite specific concepts from the context. If the answer is not in the provided context, say so explicitly.Also try to be to teh point . dont over say anything"
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
            model="openai/gpt-oss-20b",
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