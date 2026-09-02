# Setup Instructions for the UNSDG Classifier Tool

## Prerequisites
 
- [Node.js](https://nodejs.org/) v18 or higher, with npm
- [Python](https://www.python.org/) 3.10+ with `pip` and `venv`
- Git
- Optional: a GitHub personal access token (raises the GitHub API rate limit when fetching repos) and a [Groq](https://console.groq.com/) API key (enables LLM-generated README summaries — the app falls back to a simpler summary without one)

## Local Setup

This app is **three separate services** you run independently, each in its own terminal: the **frontend** (Next.js), the **backend** (Flask API), and, optionally, the **models** microservice (only needed to test the "Sentence Transformer URL" classification tab).

Each service's start command (`npm run dev`, `python app.py`) is long-running — it blocks that terminal until you stop it with `Ctrl+C`. Don't chain these with `&&` or run them one after another in the same terminal; the first one never exits, so the next never starts. Instead, open a new terminal tab or window for each step below (e.g. `Cmd+T` in Terminal/iTerm on macOS) and leave each one running.

1. **Fork the repository** on GitHub, then clone your fork:
   ```bash
   git clone https://github.com/<your-username>/UNSDG-classifier-tool.git
   cd UNSDG-classifier-tool
   ```
 
2. **Add the upstream remote** so you can pull in future updates:
   ```bash
   git remote add upstream https://github.com/chaoss/UNSDG-classifier-tool.git
   ```

3. **Start the frontend** (terminal 1):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The app will be running at `http://localhost:3000`. There's no root-level `package.json` — always run `npm` commands from inside `frontend/`, not the repo root.

4. **Start the backend** (terminal 2):
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
   The API will be running at `http://localhost:5000`.

   Optional — to enable a GitHub token and/or LLM summaries, create `backend/.env` (there's no `.env.example`; both variables are optional and the app degrades gracefully without them):
   ```
   GITHUB_TOKEN=your_token_here
   GROQ_API_KEY=your_key_here
   ```

5. **(Optional) Start the models microservice** (terminal 3) — only needed for the "Sentence Transformer URL" tab; the "Aurora Model" tab works with just the frontend + backend:
   ```bash
   cd models
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
   This loads a Hugging Face model at startup and serves it at `http://localhost:9010`. The first run downloads model weights, so expect it to take a few minutes.