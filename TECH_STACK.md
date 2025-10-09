# OuchMyBrain.io – Tech Stack and Architecture

## Overview
OuchMyBrain.io is a Flask-based web app that turns study materials into actionable learning experiences: professor-style lectures, podcasts, smart summaries, study schedules, and flashcards.

## Tech Stack
- **Backend**: `Flask` (Python)
  - **LLM Client**: `Together` SDK (calls open-weight and community models)
  - **TTS**: `ElevenLabs` (primary) with `gTTS` fallback
  - **PDF/Text**: `PyMuPDF` for extraction
  - **PDF Export**: `ReportLab` for cheat sheets
  - **Config**: `python-dotenv` for environment variables
- **Frontend**: Vanilla HTML/CSS/JS (no framework)
  - Templates in `templates/`
  - Modern, responsive UI with custom CSS
- **Runtime/OS**: Cross-platform (tested on Windows); Python 3.10+

## Key Files
- Backend
  - `app.py` – Flask app, routes, AI integrations, TTS, PDF export
  - `requirements.txt` – Python dependencies
  - `.env` – Environment variables (not for version control)
- Frontend (templates)
  - `templates/v3.html` – Home dashboard
  - `templates/teacher.html` – Professor Mode (slides + synced audio)
  - `templates/time.html` – Study Scheduler + cheat sheet download
  - `templates/smart.html` – Level-based Smart Summary
  - `templates/podcast.html` – Podcast Mode (script + audio)
  - `templates/flash.html` – AI Flashcards
- Static
  - `static/audio/` – Generated MP3 files
  - `sessions/` – Saved professor sessions (JSON)

## Environment Variables (.env)
- `TOGETHER_API_KEY` – Together API key used by the LLM client
- `ELEVENLABS_API_KEY` – ElevenLabs API key (optional if using fallback)
- `ELEVENLABS_VOICE_ID` – Default ElevenLabs voice ID (e.g. `21m00Tcm4TlvDq8ikWAM`)

Example `.env`:
```
TOGETHER_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

## Models and Features
- Summaries: `openai/gpt-oss-20b`
- Smart Summary: `openai/gpt-oss-20b`
- Professor Slides: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`
- Study Schedule: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`
- Flashcards: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`
- Podcast Script: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`
- TTS: ElevenLabs (`eleven_turbo_v2`), fallback to gTTS when needed

Notes:
- 70B models produce stronger long-form structure, JSON fidelity; 20B used for faster/cheaper summaries.
- gTTS fallback is automatic in:
  - `POST /api/text-to-speech`
  - `POST /api/generate-professor-audio`

## HTTP Routes
- Pages
  - `GET /` → `v3.html`
  - `GET /teacher` → `teacher.html`
  - `GET /time` → `time.html`
  - `GET /smart` → `smart.html`
  - `GET /podcast` → `podcast.html`
  - `GET /flash` → `flash.html`

- APIs (selected)
  - `POST /api/process` – Extract text from PDF + summary (20B)
  - `POST /api/chat` – Professor Q&A (70B)
  - `POST /api/generate-schedule` – Study plan JSON (70B)
  - `POST /api/schedule` – Alias to generate schedule
  - `POST /api/generate-flashcards` – JSON flashcards (70B)
  - `POST /api/generate-podcast-script` – Long-form script (70B)
  - `POST /api/text-to-speech` – TTS (ElevenLabs → gTTS fallback)
  - `POST /api/generate-professor-slides` – Slides JSON (70B)
  - `POST /api/generate-professor-audio` – TTS for lecture (ElevenLabs → gTTS fallback)
  - `POST /api/download-cheatsheet` – PDF via ReportLab

## Running Locally
1. Create and activate a virtual environment (recommended)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` with your keys (see example)
4. Start the app:
   ```bash
   python app.py
   ```
5. Open `http://127.0.0.1:5000/`

## Deployment Notes
- Ensure `static/audio/` and `sessions/` are writable
- Do not commit `.env`
- Rotate leaked keys immediately

## Troubleshooting
- TTS quota errors (ElevenLabs): fallback to gTTS is automatic
- Slow responses: reduce `max_tokens`, trim input context, or use fewer slides/cards
- 404s on links: confirm a single Flask app instance and that routes in `app.py` match the template links
