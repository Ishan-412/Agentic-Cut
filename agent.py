"""
agent.py — Agentic-Cut Backend
Multi-agent LangGraph pipeline: Planner → Coder → Guardrail → Executor
with self-healing retry loop (max 3 retries).
Compatible with MoviePy 2.x.
"""

import ast
import os
import re
import traceback
from pathlib import Path
from typing import TypedDict, Generator, Any

# ---------------------------------------------------------------------------
# Optional: load .env for local development
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# LangGraph & LangChain imports
# ---------------------------------------------------------------------------
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# ---------------------------------------------------------------------------
# MoviePy 2.x — used for metadata extraction only in this file
# ---------------------------------------------------------------------------
from moviepy import VideoFileClip

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_CHEATSHEET_PATH = _HERE / "moviepy_cheatsheet.txt"


def _load_cheatsheet() -> str:
    """Load the MoviePy cheatsheet for RAG injection."""
    if _CHEATSHEET_PATH.exists():
        return _CHEATSHEET_PATH.read_text(encoding="utf-8")
    return "# Cheatsheet not found — use standard moviepy.editor API."


# ============================================================
# 1. STATE SCHEMA
# ============================================================

class State(TypedDict):
    user_prompt: str
    video_path: str
    output_path: str
    model_name: str         # Gemini model to use
    quality: str            # 'high' | 'medium' | 'fast'
    edit_plan: str
    generated_code: str
    error_message: str
    render_status: str      # 'Pending' | 'Success' | 'Failed' | 'SecurityError'
    retries: int
    render_duration: float  # seconds taken to execute
    logs: list              # Accumulated log lines for the UI


# ============================================================
# 2. SECURITY GUARDRAIL
# ============================================================

BANNED_MODULES = {
    "os", "subprocess", "sys", "shutil", "socket",
    "builtins", "importlib", "ctypes", "multiprocessing",
    "threading", "signal", "pty", "atexit", "pathlib",
}

BANNED_BUILTINS = {"eval", "exec", "compile", "__import__", "open"}


class SecurityException(Exception):
    """Raised when generated code contains unsafe patterns."""
    pass


def check_code_safety(code: str) -> None:
    """
    Parse code with AST and block any imports of banned modules
    or calls to banned builtins. Raises SecurityException on violation.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SecurityException(f"Code has a syntax error: {e}") from e

    for node in ast.walk(tree):
        # Check import statements
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BANNED_MODULES:
                    raise SecurityException(
                        f"Blocked: import of banned module '{alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module in BANNED_MODULES:
                raise SecurityException(
                    f"Blocked: from '{node.module}' import — banned module"
                )
        # Check for banned builtin calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BANNED_BUILTINS:
                    raise SecurityException(
                        f"Blocked: call to banned builtin '{node.func.id}()'"
                    )
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in BANNED_BUILTINS:
                    raise SecurityException(
                        f"Blocked: call to banned attribute '{node.func.attr}()'"
                    )


# ============================================================
# 3. VIDEO METADATA EXTRACTION
# ============================================================

def sanitize_video(video_path: str) -> str:
    """
    Pre-convert problematic video formats (HEVC, Apple QuickTime .MOV, etc.)
    to a standard H.264 MP4 that MoviePy can reliably parse.

    iPhone videos in particular use HEVC (H.265) with Apple-specific QuickTime
    metadata that triggers a float+str TypeError inside moviepy's ffmpeg_reader.
    Re-encoding to H.264 MP4 strips that metadata and fixes the issue.

    Returns the path to the sanitized file (may be the same path if no
    conversion was needed).
    """
    import subprocess
    path = Path(video_path)
    ext = path.suffix.lower()

    # Detect HEVC/MOV files that need conversion
    needs_conversion = ext in {".mov", ".hevc", ".m4v"}
    if not needs_conversion:
        # Also probe for HEVC codec even in .mp4 containers
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1",
                 str(path)],
                capture_output=True, text=True, timeout=10
            )
            if "hevc" in probe.stdout.lower():
                needs_conversion = True
        except Exception:
            pass

    if not needs_conversion:
        return video_path

    out_path = path.with_suffix("").with_name(path.stem + "_safe.mp4")
    if out_path.exists():
        return str(out_path)

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(path),
                "-c:v", "libx264",       # Re-encode video to H.264
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",           # Re-encode audio to AAC
                "-map_metadata", "-1",   # Strip all Apple/QuickTime metadata
                "-movflags", "+faststart",
                str(out_path),
            ],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and out_path.exists():
            return str(out_path)
        else:
            # Conversion failed — return original and let MoviePy try
            return video_path
    except Exception:
        return video_path


def get_video_metadata(video_path: str) -> dict:
    """Extract basic metadata from a video file using MoviePy.
    Sanitizes HEVC/MOV files first to avoid Apple QuickTime metadata bugs."""
    try:
        safe_path = sanitize_video(video_path)
        clip = VideoFileClip(safe_path)
        meta = {
            "duration": round(clip.duration, 2),
            "fps": round(clip.fps, 2),
            "width": clip.size[0],
            "height": clip.size[1],
            "size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 2),
            "sanitized_path": safe_path,   # Pass sanitized path downstream
        }
        clip.close()
        return meta
    except Exception as e:
        return {"error": str(e), "duration": 0, "fps": 24, "width": 0, "height": 0, "size_mb": 0}



# ============================================================
# 4. LLM FACTORY
# ============================================================

def _extract_text(content) -> str:
    """
    Extract plain text from a LangChain response content.
    Newer Gemini models via langchain-google-genai may return a list of
    content parts rather than a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
            else:
                # AIMessageChunk or similar — try .text attribute
                parts.append(getattr(part, "text", str(part)))
        return "".join(parts)
    return str(content)


def _get_llm(api_key: str, model_name: str = "gemini-1.5-pro") -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1,
    )

def _safe_invoke(api_key: str, model_name: str, messages: list):
    try:
        llm = _get_llm(api_key, model_name)
        return llm.invoke(messages)
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "404" in error_msg or "PERMISSION_DENIED" in error_msg or "NOT_FOUND" in error_msg:
            fallback_model = "gemini-2.0-flash"
            if model_name != fallback_model:
                print(f"Model {model_name} failed with {error_msg}. Falling back to {fallback_model}.")
                llm = _get_llm(api_key, fallback_model)
                return llm.invoke(messages)
        raise e


# ============================================================
# 5. NODE: PLANNER AGENT
# ============================================================

def plan_node(state: State, api_key: str) -> State:
    """
    Converts user_prompt + video metadata into a step-by-step edit plan.
    """
    logs = list(state.get("logs", []))
    logs.append("🧠 [Planner] Starting planning phase...")

    meta = get_video_metadata(state["video_path"])
    logs.append(
        f"📹 [Planner] Video metadata — Duration: {meta.get('duration')}s | "
        f"FPS: {meta.get('fps')} | Resolution: {meta.get('width')}x{meta.get('height')} | "
        f"Size: {meta.get('size_mb')} MB"
    )

    system_prompt = """You are an expert video editing planner. Your job is to convert a user's
natural-language video editing request into a structured, numbered step-by-step execution plan.

Be specific and technical. Each step should reference exact MoviePy operations.
Format your plan clearly in Markdown with numbered steps.

Rules:
- Keep the plan concise (3-8 steps maximum).
- Do NOT write any Python code — only describe the steps.
- Reference exact parameter values where known (e.g., "trim from 0s to 5s", "speed 1.5x").
- Always end with a step: "Write the final output to `output_path`."
"""

    human_message = f"""User Request: {state['user_prompt']}

Video File: {state['video_path']}
Video Metadata:
- Duration: {meta.get('duration')} seconds
- FPS: {meta.get('fps')}
- Resolution: {meta.get('width')}x{meta.get('height')} pixels
- File Size: {meta.get('size_mb')} MB

Please create a step-by-step editing plan."""

    response = _safe_invoke(
        api_key,
        state.get("model_name", "gemini-2.0-flash"),
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message),
        ]
    )

    edit_plan = _extract_text(response.content)
    logs.append("✅ [Planner] Edit plan generated successfully.")

    # Use the sanitized path (H.264 MP4) for all downstream nodes
    safe_path = meta.get("sanitized_path", state["video_path"])
    if safe_path != state["video_path"]:
        logs.append(f"🔄 [Planner] Converted HEVC/MOV → H.264 MP4 for compatibility.")

    return {
        **state,
        "video_path": safe_path,   # Downstream nodes use the safe file
        "edit_plan": edit_plan,
        "logs": logs,
    }


# ============================================================
# 6. NODE: CODER AGENT
# ============================================================

def code_node(state: State, api_key: str) -> State:
    """
    Converts the edit_plan into executable Python MoviePy code.
    On retry, appends error traceback to the prompt for self-healing.
    """
    logs = list(state.get("logs", []))
    retries = state.get("retries", 0)

    if retries == 0:
        logs.append("⚙️  [Coder] Generating MoviePy code from plan...")
    else:
        logs.append(f"🔄 [Coder] Auto-correcting code (attempt {retries + 1}/3)...")

    cheatsheet = _load_cheatsheet()

    quality = state.get("quality", "high")
    quality_hints = {
        "high":   "Use the original fps and highest quality codec settings.",
        "medium": "Use fps=24 and standard codec settings for a balance of quality and speed.",
        "fast":   "Use fps=24 and prioritize fast encoding over maximum quality.",
    }.get(quality, "")

    system_prompt = f"""You are an expert Python video editing programmer specializing in MoviePy.
Your job is to write a complete, executable Python script using the moviepy library.

IMPORTANT RULES:
1. Output ONLY raw Python code — no markdown fences, no explanations, no comments beyond inline ones.
2. Use ONLY the moviepy library for video operations.
3. The input video path is available as a Python variable: `video_path` (string).
4. The output path is available as a Python variable: `output_path` (string).
5. Both `video_path` and `output_path` are already defined in the execution scope — do NOT redefine them.
6. NEVER import or use: os, subprocess, sys, shutil, socket, eval, exec, open.
7. Always call `write_videofile(output_path, codec='libx264', audio_codec='aac', fps=clip.fps, logger=None)`.
8. Always close all clips at the end with `.close()`.
9. Use ONLY the methods and patterns shown in the reference below.
10. Quality preference: {quality_hints}

--- MOVIEPY REFERENCE (USE ONLY THESE METHODS) ---
{cheatsheet}
--- END OF REFERENCE ---
"""

    if retries > 0 and state.get("error_message"):
        error_section = f"""
PREVIOUS ATTEMPT FAILED WITH THIS ERROR:
```
{state['error_message']}
```
Fix the code. The error above is the EXACT traceback. Identify the root cause and correct it.
Do NOT repeat the same mistake. Output only the corrected Python code.
"""
    else:
        error_section = ""

    human_message = f"""Edit Plan to implement:
{state['edit_plan']}

{error_section}
Write the complete Python script now."""

    response = _safe_invoke(
        api_key,
        state.get("model_name", "gemini-2.0-flash"),
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message),
        ]
    )

    raw_code = _extract_text(response.content)

    # Strip any accidental markdown fences the model may have added
    raw_code = re.sub(r"^```(?:python)?\n?", "", raw_code.strip())
    raw_code = re.sub(r"\n?```$", "", raw_code.strip())

    logs.append("✅ [Coder] Code generation complete.")
    logs.append(f"📝 [Coder] Generated {len(raw_code.splitlines())} lines of code.")

    return {
        **state,
        "generated_code": raw_code,
        "logs": logs,
    }


# ============================================================
# 7. NODE: EXECUTION & GUARDRAIL
# ============================================================

def execute_node(state: State) -> State:
    """
    1. Run AST security scan.
    2. Execute via exec() in sandboxed namespace.
    3. Capture output, update render_status.
    """
    logs = list(state.get("logs", []))
    retries = state.get("retries", 0)
    code = state.get("generated_code", "")

    logs.append("🔒 [Guardrail] Running AST security scan...")

    # --- Security check ---
    try:
        check_code_safety(code)
        logs.append("✅ [Guardrail] Security scan passed — no unsafe patterns detected.")
    except SecurityException as se:
        logs.append(f"🚨 [Guardrail] SECURITY VIOLATION: {se}")
        return {
            **state,
            "error_message": f"SecurityException: {se}",
            "render_status": "SecurityError",
            "logs": logs,
        }

    # --- Execution ---
    logs.append("🎬 [Executor] Executing generated MoviePy script...")

    # Namespace for exec: pre-inject video_path and output_path
    exec_namespace: dict[str, Any] = {
        "video_path": state["video_path"],
        "output_path": state["output_path"],
    }

    import time as _time
    t_start = _time.time()
    try:
        exec(code, exec_namespace)  # noqa: S102
        duration = round(_time.time() - t_start, 1)
        logs.append(f"✅ [Executor] Render completed successfully in {duration}s!")
        return {
            **state,
            "render_status": "Success",
            "error_message": "",
            "render_duration": duration,
            "logs": logs,
        }
    except Exception:
        duration = round(_time.time() - t_start, 1)
        tb = traceback.format_exc()
        logs.append(f"❌ [Executor] Execution failed (attempt {retries + 1}/3):\n{tb}")
        return {
            **state,
            "render_status": "Failed",
            "error_message": tb,
            "retries": retries + 1,
            "render_duration": duration,
            "logs": logs,
        }


# ============================================================
# 8. CONDITIONAL EDGE ROUTER
# ============================================================

def router_edge(state: State) -> str:
    """
    Determines next node based on render_status and retry count.
    Returns the name of the next node or END.
    """
    status = state.get("render_status", "Pending")
    retries = state.get("retries", 0)

    if status == "Success":
        return END
    elif status == "SecurityError":
        return END
    elif status == "Failed" and retries < 3:
        return "code_node"
    else:
        # Max retries exceeded or unknown status
        return END


# ============================================================
# 9. GRAPH ASSEMBLY
# ============================================================

def build_graph(api_key: str, model_name: str = "gemini-2.0-flash", quality: str = "high") -> StateGraph:
    """Build and compile the LangGraph state machine."""

    graph = StateGraph(State)

    def _plan(s: State) -> State:
        return plan_node(s, api_key)

    def _code(s: State) -> State:
        return code_node(s, api_key)

    graph.add_node("plan_node", _plan)
    graph.add_node("code_node", _code)
    graph.add_node("execute_node", execute_node)

    graph.set_entry_point("plan_node")
    graph.add_edge("plan_node", "code_node")
    graph.add_edge("code_node", "execute_node")
    graph.add_conditional_edges(
        "execute_node",
        router_edge,
        {
            "code_node": "code_node",
            END: END,
        },
    )

    return graph.compile()


# ============================================================
# 10. PUBLIC API — Used by app.py
# ============================================================

def run_agent(
    video_path: str,
    prompt: str,
    api_key: str,
    output_path: str = "final_output.mp4",
    model_name: str = "gemini-2.0-flash",
    quality: str = "high",
) -> Generator[dict, None, None]:
    """
    Run the full agentic pipeline and yield intermediate state dicts
    after each node completes, for live Streamlit display.
    """
    compiled = build_graph(api_key, model_name, quality)

    initial_state: State = {
        "user_prompt": prompt,
        "video_path": video_path,
        "output_path": output_path,
        "model_name": model_name,
        "quality": quality,
        "edit_plan": "",
        "generated_code": "",
        "error_message": "",
        "render_status": "Pending",
        "retries": 0,
        "render_duration": 0.0,
        "logs": [],
    }

    for step_output in compiled.stream(initial_state):
        for node_name, node_state in step_output.items():
            yield {"node": node_name, "state": node_state}


# ============================================================
# 11. STANDALONE TEST ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import sys

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: Set GOOGLE_API_KEY environment variable before running.")
        sys.exit(1)

    video = "sample_input.mp4"
    if not Path(video).exists():
        print(f"ERROR: '{video}' not found. Run `python generate_sample.py` first.")
        sys.exit(1)

    prompt = "Trim the first 1 second and save output."
    print(f"\n{'='*60}")
    print(f"  Agentic-Cut — Standalone Test")
    print(f"  Prompt: {prompt}")
    print(f"{'='*60}\n")

    final_state = None
    for update in run_agent(video, prompt, api_key, output_path="final_output.mp4"):
        node = update["node"]
        state = update["state"]
        for log_line in state.get("logs", []):
            print(log_line)
        final_state = state

    print(f"\n{'='*60}")
    if final_state and final_state.get("render_status") == "Success":
        output = final_state.get("output_path", "final_output.mp4")
        print(f"  ✅ SUCCESS — Output: {output}")
        if Path(output).exists():
            size = Path(output).stat().st_size / 1024
            print(f"  📁 File size: {size:.1f} KB")
    else:
        print(f"  ❌ FAILED — Status: {final_state.get('render_status')}")
        print(f"  Error: {final_state.get('error_message', 'Unknown')[:500]}")
    print(f"{'='*60}\n")
