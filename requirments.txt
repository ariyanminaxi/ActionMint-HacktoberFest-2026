# REQUIREMENTS.txt — one file, everything the project needs.
# Python and Node don't share an installer, so this file documents both; the actual installs
# still run as two separate commands (shown below each section).

# =========================================================
# SYSTEM (install once, outside the project)
# =========================================================
# - Python 3.11+
# - Node.js 20+ and npm
# - git
# - Ollama (https://ollama.com) — local model fallback
# - cloudflared is downloaded automatically by the Kaggle notebooks; nothing to install here

# =========================================================
# BACKEND (Python) — backend/requirements.txt
# Install:  cd backend && pip install -r requirements.txt --break-system-packages
# =========================================================
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
slowapi==0.1.9
httpx==0.28.1
google-genai==0.3.0
numpy==1.26.4
scikit-learn==1.5.2
sentence-transformers==3.3.1
python-multipart==0.0.20
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.25.0

# =========================================================
# FRONTEND (Node) — installed into frontend/package.json
# Install:  cd frontend && npm install <each package below>   (or npm install if package.json
# already lists them, e.g. after cloning)
# =========================================================
# --- dependencies ---
react
react-dom
react-router-dom
zustand
zod
gsap
lenis
react-markdown
rehype-sanitize
@fontsource/<your-chosen-fonts>

# --- devDependencies (npm install -D) ---
typescript
vite
@vitejs/plugin-react
tailwindcss
postcss
autoprefixer
eslint
vitest
@testing-library/react

# =========================================================
# IMAGE SCRIPT (Python) — only needed to run scripts/keyout.py
# Install:  pip install pillow numpy --break-system-packages
# =========================================================
pillow
numpy

# =========================================================
# MODEL (local fallback)
# =========================================================
# ollama pull gemma4:e2b        (fits 6 GB VRAM laptops)
# ollama pull gemma4:e4b        (optional, ~9.6 GB, partly runs on CPU with 6 GB VRAM)

# =========================================================
# SECRETS — names only, real values go in model/.env.model (git-ignored, see .env.model.example)
# =========================================================
# APP_TOKEN, GEMINI_API_KEY, GROQ_API_KEY, KAGGLE_GATEWAY_URL, STUDIO_URL
