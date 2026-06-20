# TalkBuddy Production Environment Configuration

This guide lists the environment variables you need to configure on **Hugging Face Spaces (Backend)** and **Render (Frontend)** for a successful production deployment.

---

## 1. Backend: Hugging Face Spaces Configuration
In your Hugging Face Space, navigate to **Settings** > **Variables and Secrets** and add the following keys.

### Essential Variables
| Key | Type | Example Value / Description |
| :--- | :--- | :--- |
| `ENV` | Variable | `production` (Turns off dev server hot-reloading to save RAM) |
| `SECRET_KEY` | Secret | Any long random string (e.g., `d2389ab2d8c3e859f81a7d6e5c83b8e4`) to sign JWT tokens |

### Database Settings (Recommended)
Since Hugging Face container storage is wiped on restart, we recommend using a free PostgreSQL database from [Supabase](https://supabase.com) or [Neon](https://neon.tech).
| Key | Type | Example Value / Description |
| :--- | :--- | :--- |
| `DB_URL` | Secret | `postgresql://postgres:yourpassword@db.supabase.co:5432/postgres` (Unified connection string) |

*Note: If `DB_URL` is omitted, the app will fall back to local SQLite, but your chat logs and user registrations will be wiped when the Space restarts or goes to sleep.*

### LLM Coaching Brain Settings
Since local Ollama Llama 3.1 8B cannot run on the free Hugging Face CPU tier, configure the OpenAI-compatible path to query **Groq** (Recommended - ultra fast) or **Hugging Face Serverless Inference API** (Free with a user token).

#### Option A: Groq API (Recommended for performance)
| Key | Type | Value |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | Variable | `openai` |
| `LLM_API_KEY` | Secret | `gsk_your_groq_api_key_here` (Get a free key from console.groq.com) |
| `LLM_API_URL` | Variable | `https://api.groq.com/openai/v1/chat/completions` |
| `LLM_MODEL` | Variable | `llama-3.1-8b-instant` |

#### Option B: Hugging Face Serverless Inference API
| Key | Type | Value |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | Variable | `openai` |
| `LLM_API_KEY` | Secret | `hf_your_huggingface_user_token_here` (Generate a write/read token in HF settings) |
| `LLM_API_URL` | Variable | `https://api-inference.huggingface.co/v1/chat/completions` |
| `LLM_MODEL` | Variable | `meta-llama/Llama-3.1-8B-Instruct` |

---

## 2. Frontend: Render (Static Sites) Configuration
In your Render Dashboard, when deploying the React static site, add these variables in the **Environment** section of your Web Service.

| Key | Value / Description |
| :--- | :--- |
| `VITE_API_URL` | Direct HTTPS URL of your Hugging Face Space (e.g. `https://sachinyadav8953-talkbuddy.hf.space`) |
| `VITE_WS_URL` | (Optional) WebSocket endpoint. Derived automatically from `VITE_API_URL` if omitted (e.g. `wss://sachinyadav8953-talkbuddy.hf.space`) |

---

## 3. How to Deploy

### Step 1: Deploy Backend to Hugging Face
1. Create a new **Space** on Hugging Face (huggingface.co/spaces).
2. Give it a name, select **Docker** as the SDK, and choose **Blank** (or choose any free template).
3. Under space hardware, select the free CPU tier (**CPU basic · 2 vCPU · 16 GB RAM · Free**).
4. Add the **Variables and Secrets** listed in Section 1 above under Space Settings.
5. Clone your space repository locally or upload your files via git directly to the Space. Only push the contents of the `backend/` directory (ensure the Dockerfile, requirements.txt, and app/ folder are at the root of your Hugging Face repository).

### Step 2: Deploy Frontend to Render
1. Create a new **Static Site** on Render (render.com).
2. Connect your Git repository.
3. Configure the following build settings:
   * **Root Directory:** `frontend`
   * **Build Command:** `npm run build`
   * **Publish Directory:** `dist`
4. Add the `VITE_API_URL` environment variable under the Environment settings.
5. Click deploy!
