<div align="center">
  <h1>🎬 Agentic-Cut</h1>
  <p><strong>Autonomous Multi-Agent AI Video Editor</strong></p>
  
  <p>
    <a href="#about">About</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#features">Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#installation">Installation</a>
  </p>
</div>

---

## 📖 About
**Agentic-Cut** is an open-source, enterprise-ready multi-agent video editing platform. It allows users to upload raw video files and apply edits using **natural language commands**. Instead of relying on a rigid, hardcoded backend, Agentic-Cut uses an autonomous multi-agent pipeline to interpret user intent, generate a structured plan, dynamically write Python code using MoviePy, and render the final video locally.

Designed to be a showstopper portfolio piece, the platform boasts a highly interactive, beautifully animated Streamlit frontend that feels like a native app.

## ⚙️ How It Works
Agentic-Cut operates on a robust **4-Stage Multi-Agent Pipeline** built on **LangGraph**. When a user submits an instruction (e.g., *"Trim the first 3 seconds, convert to grayscale, and speed up 2x"*), the following happens:

1. 🧠 **Planner Agent**: Analyzes the request alongside the video metadata (duration, FPS, resolution) and breaks the intent down into a structured, step-by-step editing plan.
2. ⚙️ **Coder Agent**: Uses the plan and a highly constrained context window (via Vectorless RAG from a verified `moviepy_cheatsheet.txt`) to generate raw, executable `MoviePy` Python code.
3. 🔒 **Guardrail System**: Performs a strict Abstract Syntax Tree (AST) scan on the generated code. It immediately blocks any destructive modules (like `os`, `sys`, `subprocess`, or `eval`), ensuring zero remote-code-execution (RCE) vulnerabilities.
4. 🎬 **Executor Agent**: Runs the verified code in an isolated execution namespace.
5. 🔄 **Self-Healing Loop**: If the executor encounters a Python runtime error (e.g., a missing variable or a MoviePy specific exception), the exact traceback is routed *back* to the Coder Agent. The AI autonomously debugs and fixes its own code, retrying up to 3 times without human intervention.

## ✨ Features
* **Natural Language Video Editing**: Describe what you want, and the AI does the rest.
* **Auto-Recovery**: Built-in self-healing loop that fixes code errors on the fly.
* **100% Free Tier Architecture**: Designed to run flawlessly on free hosting platforms (Streamlit Community Cloud) using Google Gemini's free tier.
* **Stunning UI/UX**: Features a highly polished, glassmorphism-inspired dark theme with staggered animations, interactive particle backgrounds, and real-time pipeline status indicators.
* **Agent Inspector**: Transparently view the exact plans, generated code, and execution logs in real-time.

## 🛠 Tech Stack
This project leverages a modern, Python-centric AI stack:

### AI & Orchestration
* **[LangGraph](https://python.langchain.com/docs/langgraph)** - Orchestrates the state machine, defining the multi-agent flow and conditional routing (the self-healing loop).
* **[LangChain](https://python.langchain.com/)** - Handles the core LLM wrapping and message formatting.
* **[Google Gemini (1.5 Flash / 3.1 Pro)](https://aistudio.google.com/)** - The underlying LLM engine powering the intelligence, chosen for its massive context window and exceptional code generation capabilities.

### Video Processing
* **[MoviePy 2.x](https://zulko.github.io/moviepy/)** - The core Python library used for non-linear video editing (cutting, concatenating, audio manipulation, FX).
* **[FFmpeg](https://ffmpeg.org/)** - The underlying engine MoviePy relies on to decode and encode the video files.

### Frontend
* **[Streamlit](https://streamlit.io/)** - The rapid web app framework. Heavily customized with massive raw CSS/HTML injections to bypass standard limitations and achieve a premium, animation-heavy portfolio look.

## 🚀 Installation & Local Usage

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Agentic-Cut.git
   cd Agentic-Cut
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set your Google API Key**
   Create a `.env` file in the root directory and add your key:
   ```env
   GOOGLE_API_KEY="your_gemini_api_key_here"
   ```

4. **Run the Application**
   ```bash
   streamlit run app.py
   ```
   *The app will automatically launch in your default web browser.*
