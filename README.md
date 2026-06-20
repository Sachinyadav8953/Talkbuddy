# TalkBuddy: AI English Speaking Coach 🎙️

TalkBuddy is a full-stack, real-time voice coaching application designed to help users practice their spoken English. It leverages 100% free and open-source local AI models:
- **Speech-to-Text**: Whisper (`faster-whisper` implementation)
- **Conversational AI / Grammar Evaluator**: Llama 3.1 8B Instruct (via Ollama)
- **Text-to-Speech**: Piper TTS

For every spoken sentence, the coach transcribes your speech, rates your Grammar, Vocabulary, and Fluency, corrects your mistakes with simple grammar explanations, suggests better vocabulary options, and speaks back to you.

---

## Architecture Diagram

- **Frontend**: React + TypeScript + Tailwind CSS (Vite bundler)
- **Backend**: FastAPI + WebSockets for real-time speech streaming
- **Database**: PostgreSQL (SQLAlchemy ORM)

---

## 🛠️ Prerequisites

Before starting, make sure you have the following installed on your host system:

1. **Node.js** (v18 or newer)
2. **Python** (v3.10 or newer)
3. **Ollama** (Downloaded and running)
4. **FFmpeg** (Required for audio processing by Whisper)
   - **Windows**: Install via `winget install Gyan.FFmpeg` or download static builds and add the `/bin` folder to your Path.
   - **Ubuntu/Debian**: `sudo apt-get install -y ffmpeg`
   - **macOS**: `brew install ffmpeg`

---

## 🧠 Pulling Llama 3.1 in Ollama

TalkBuddy relies on Ollama running on the host system to run Llama 3.1 8B.
Ensure Ollama is running and download the model:

```bash
ollama pull llama3.1
```

---

## 🚀 Option 1: Running Locally (Recommended for Development)

### 1. Database Setup
Create a PostgreSQL database named `talkbuddy` on your local instance. The backend is preconfigured to connect to `localhost:5432` with user `postgres` and password `postgres`.
*(If you want to use custom database credentials, you can set the environment variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, etc., in a `.env` file inside the `backend` folder).*

### 2. Backend Installation & Startup
Open a terminal inside the `./backend` directory:
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run backend
python run.py
```
*Note: On server startup, the backend will automatically detect your OS, download the precompiled Piper TTS binary, and download the `en_US-lessac-medium` ONNX model and config. This may take a few moments on the first launch.*

### 3. Frontend Installation & Startup
Open a new terminal inside the `./frontend` directory:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🐳 Option 2: Running with Docker Compose

You can spin up the entire application including the PostgreSQL database using Docker Compose.

1. Ensure Ollama is running on your host machine.
2. In the root directory of the project, run:
```bash
docker-compose up --build
```
This commands will spin up:
- **Database**: PostgreSQL on port `5432`
- **Backend**: FastAPI on port `8000`
- **Frontend**: Serves the compiled React app on port `3000`

Open `http://localhost:3000` in your browser.

---

## ⚙️ Configuration (Environment Variables)

The following environment variables can be adjusted:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `POSTGRES_USER` | PostgreSQL Username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL Password | `postgres` |
| `POSTGRES_HOST` | Database Host Address | `localhost` (API) / `db` (Compose) |
| `POSTGRES_PORT` | Database Port | `5432` |
| `POSTGRES_DB` | Database Schema Name | `talkbuddy` |
| `OLLAMA_URL` | Ollama service endpoint | `http://localhost:11434` / `http://host.docker.internal:11434` |
| `WHISPER_MODEL` | Whisper model accuracy level | `base` (can use `tiny`, `small`, `medium`) |
| `WHISPER_DEVICE` | Hardware device for STT | `cpu` (use `cuda` if you have a GPU) |

---

## 🎤 How to Use TalkBuddy

1. **Register & Log In**: Create a student account.
2. **Select Coaching Mode**: Choose a scenario from **Casual Talk**, **Job Interview Prep**, **IELTS Speaking exam**, **Business English**, or **Daily Scenarios**.
3. **Start Recording**: Click the Microphone button and start speaking in English. You will see active sound waves representing your volume.
4. **Submit Speech**: Click the button again to stop. Your speech is immediately streamed, transcribed, and evaluated.
5. **Get Instant Audio & Text Feedback**: Auto-play will read out the coach's answer. The page updates with:
   - What you said vs how to correct it.
   - An easy-to-understand grammar explanation.
   - A selection of vocabulary suggestions to sound more native.
   - Separate Grammar, Vocabulary, and Fluency scores.
6. **Dashboard**: Navigate to the Dashboard to track your scores progress over time on visual progress charts.
