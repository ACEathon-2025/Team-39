# 🌟 OuchMyBrain.io — Smart AI Study Assistant  
**Empowering students to learn smarter, not harder.**  

Leverage cutting-edge **AI** to make study sessions more effective and less time-consuming.  
Effortlessly transform any study material into engaging summaries, flashcards, audio lessons, and adaptive quizzes — all personalized to your pace and style.

---

## 📘 Overview  

OuchMyBrain.io is your **AI-powered study companion** that transforms raw materials into interactive learning experiences.  
It supports multiple learning modes — **reading, listening, testing, and planning** — while adapting dynamically to your progress.

> ✨ Learn efficiently.  
> 🎧 Listen intuitively.  
> 💬 Revise interactively.  
> 🧩 Plan intelligently.

---

## 🧠 Core Features  

### 📝 1. PDF & Document Upload and Processing  
- Upload **PDFs, lecture notes, slides, textbooks**, and more.  
- Automatically extracts text and organizes it by **chapters, sections, and headings**.  
- Supports **PDF, DOCX, TXT, EPUB** formats.  

---

### ⚡ 2. Smart Summarization Engine  
- Generates **5-level summaries** based on study time or depth required.  
- Focuses on important topics using **adaptive AI compression**.  
- Highlights **key terms, definitions, and formulas** for quick reference.  
- Context-aware summaries designed for **quizzes, flashcards, and audio lessons**.  

---

### 🎴 3. Flashcard Generator  
- Automatically generates **Q&A**, **cloze deletion**, and **image-based** flashcards.  
- Integrated with **spaced repetition algorithms** for long-term memory.  
- Export and sync with your favorite flashcard apps.  

---

### 💬 4. AI Chatbot with Content Awareness  
- Conversational assistant that **understands your uploaded content**.  
- Maintains context in **multi-turn dialogues**.  
- Supports **voice and text** interactions.  

---

### 🎙️ 5. Voice Professor Mode  
- Converts summaries into **interactive audio lectures**.  
- Includes **voice commands**, **difficulty adjustment**, and **gamified lessons**.  
- Great for auditory learners or hands-free studying.  

---

### 🎧 6. Podcast Mode  
- Converts study materials into **natural-sounding audio podcasts**.  
- Create playlists, download offline, and listen in multiple languages.  

---

### 🌍 7. Multilingual Support  
- Translate and study in **multiple languages**.  
- Choose **voice modes, accents**, and translation levels.  

---

### 🧭 8. Personalized Learning Path  
- AI builds your **custom study roadmap** based on goals, performance, and preferences.  
- Dynamically adjusts as your progress evolves.  

---

### ✏️ 9. Note-Taking & Highlighting  
- Annotate, highlight, and take notes directly on uploaded content.  
- Export annotated materials for revision.  

---

### 🔗 10. Integration & Export Options  
- Export quizzes, flashcards, and summaries.  
- Seamless **LMS integration** and sharing support.  

---

### 🖥️ 11. User Interface & Accessibility  
- Sleek, mobile-friendly, and **dark-mode** enabled UI.  
- Built with accessibility and **voice command** support in mind.  

---

### 🎶 12. Contextual AI-Generated Study Music  
> “Music that thinks like your brain.”

- AI generates **personalized background soundscapes** for study sessions.  
- Modes: **Focus**, **Relax**, **Energize**.  
- Adapts to topic complexity, study intensity, and mood.  
- Enhances retention through **neuroscience-based sound design**.  

---

### 📅 13. Smart Study Scheduler & Planner  
- AI creates study schedules using:  
  - 📚 Exam dates  
  - ⏰ Available time  
  - 🎯 Target marks  
- Adjusts dynamically as deadlines or performance change.  
- Integrates with flashcards, and summaries.  
- Includes **reminders, break suggestions, and calendar sync**.  

---

## 🧩 System Architecture  

### ⚙️ Backend  
- **Flask (Python)** — API & routing.  
- **OpenAI GPT-4o / Mini**, **OpenRouter** (Anthropic, Mistral).  
- **TTS** — ElevenLabs, Coqui, or gTTS fallback.  

### 🖼️ Frontend  
- **HTML5 + Jinja2** templates.  
- **TailwindCSS** — responsive dark theme.  
- **Vanilla JS (AJAX/Fetch)** — chat, and flashcards.  

---

## 🔁 Learning Flow  

```mermaid
graph LR
A[Upload Materials] --> B[Material Processing]
B --> C[Summarization Engine]
C --> D[Professor Mode / Audio Lessons]
D --> E[Flashcards]
E --> F[AI Planner & Schedule]
F --> G[Continuous Progress Feedback]
```

---

## 🌟 Benefits  

- 🎯 Personalized & adaptive learning.  
- 🧩 Supports **visual**, **auditory**, and **active recall** learners.  
- 📈 Boosts comprehension, retention, and engagement.  
- 🔄 Streamlined workflow — from upload to mastery.  

---

## 👩‍💻 Team  

**Team:** Eroom — *Acethon Project*  
**Prototype:** [OuchMyBrain.io](#)  

> “Study smarter. Retain longer. Learn anywhere.”

---

## 🧪 New: Research Generator & PDF Exports

- **Research Paper Generator** with optional web intelligence.
  - Routes:
    - `GET /research` — research UI page.
    - `POST /api/web-research` — fetch credible web sources via DuckDuckGo HTML + BeautifulSoup.
    - `POST /api/generate-research-paper` — generate a comprehensive paper (Markdown) using Together AI LLMs.
- **PDF Export Endpoints**
  - `POST /api/download-cheatsheet` — generate a clean cheat sheet PDF from text.
  - `POST /api/download-ultimate-cheatsheet` — enhanced styling and markdown-like support.
  - `POST /api/download-flashcards` — export AI-generated flashcards as a formatted PDF.
  - (Optional) `POST /api/download-research-pdf` — recommended endpoint to export the research paper content to a styled PDF if/when added.

### Example: Web Research Request

```bash
curl -X POST http://localhost:5000/api/web-research \
  -H "Content-Type: application/json" \
  -d '{"query":"Large Language Models safety best practices","depth":5}'
```

### Example: Generate Research Paper

```bash
curl -X POST http://localhost:5000/api/generate-research-paper \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Reinforcement Learning",
    "description": "Intro + recent advances",
    "revolvesAround": "Policy gradients, model-based RL",
    "relatedTopics": "Bandits, offline RL",
    "pdfContent": "(optional content extracted from uploads)",
    "webSources": []
  }'
```

### Example: Download Flashcards PDF

```bash
curl -X POST http://localhost:5000/api/download-flashcards \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Algebra Basics",
    "flashcards": [
      {"id":1, "question":"What is a group?", "answer":"A set with an associative binary operation, identity, and inverses.", "category":"Abstract Algebra", "difficulty":"easy", "hint":"Think closure + axioms"}
    ]
  }' --output Algebra_Basics_Flashcards.pdf
```

---

## 🧰 Updated Tech Stack

- **Backend**: `Flask`
- **LLM Access**: `together` (Together AI SDK) for models like Meta Llama.
- **PDF Generation**: `reportlab` for all PDF exports (cheat sheets, flashcards, research).
- **Parsing & Research**: `beautifulsoup4` + `requests` for web results parsing.
- **PDF/Text Extraction**: `PyMuPDF`.
- **Text-to-Speech**: `elevenlabs`, `gTTS` as fallback.
- **Env Management**: `python-dotenv`.

### Environment Variables

- `TOGETHER_API_KEY` — required for research paper generation via Together AI.
- `ELEVENLABS_API_KEY` — required for ElevenLabs TTS.
- Optional standard Flask variables: `FLASK_ENV`, `PORT`.

---

## ▶️ Run Locally

```bash
pip install -r requirements.txt
python app.py
# App runs at http://127.0.0.1:5000
```

---

## Notes

- If you experience any PDF errors, ensure you are on a recent `reportlab` version (see `requirements.txt`).
- Web research uses public HTML search; results may vary by region and connectivity.
