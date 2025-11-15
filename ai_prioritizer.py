import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import time
import re

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

genai.configure(api_key=API_KEY)

MODEL_NAME = "models/gemini-2.5-flash"


# ---------------------------
# CACHING SYSTEM
# ---------------------------
_last_history_snapshot = None
_last_ai_output = None


def histories_are_equal(h1, h2):
    """Compare two history lists safely using JSON serialization."""
    return json.dumps(h1, sort_keys=True) == json.dumps(h2, sort_keys=True)


def get_ai_prioritized_tasks(history):
    global _last_history_snapshot, _last_ai_output

    # 1. If empty → baseline response
    if not history:
        _last_history_snapshot = []
        _last_ai_output = {
            "prioritized_tasks": [],
            "ai_insights": ["No patient requests yet. System is idle."],
            "wellbeing_summary": {
                "score": 10,
                "rationale": "No requests indicates stability."
            }
        }
        return _last_ai_output

    # 2. If history did NOT change → return cached result
    if _last_history_snapshot is not None:
        if histories_are_equal(history, _last_history_snapshot):
            print("ℹ️ History unchanged — using cached AI result.")
            return _last_ai_output

    # Update snapshot
    _last_history_snapshot = json.loads(json.dumps(history))

    # Build input for Gemini
    formatted_history = "\n".join(
        f"- {item['request']} at "
        f"{time.strftime('%I:%M:%S %p', time.localtime(item['timestamp']))}"
        for item in history[-10:]
    )

    prompt = f"""
You are a brilliant hospital nurse AI assistant. Analyze recent patient requests.

Recent history:
{formatted_history}

Return ONLY this exact JSON:
{{
  "prioritized_tasks": [
    {{
      "request_type": "The specific task",
      "priority": "High | Medium | Low"
    }}
  ],
  "ai_insights": [
    "Insight 1",
    "Insight 2"
  ],
  "wellbeing_summary": {{
    "score": 8,
    "rationale": "..."
  }}
}}
"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        text = response.text
        print("Gemini responded:", text)

        parsed = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```json\n(\{.*?\})\n```", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))

        if parsed is None:
            raise ValueError("Invalid JSON from AI")

        _last_ai_output = parsed
        return parsed

    except Exception as e:
        print(f"⚠️ Gemini API failed: {e}")

        fallback = {
            "prioritized_tasks": [
                {"request_type": "AI is offline. Check requests manually.", "priority": "High"}
            ],
            "ai_insights": [f"AI error: {e}"],
            "wellbeing_summary": {"score": "N/A", "rationale": "AI offline."}
        }

        _last_ai_output = fallback
        return fallback
