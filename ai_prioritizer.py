# ai_prioritizer.py
import time
import json
from typing import List, Dict
from google import genai
from google.genai import types

# -------------------------------------------------
# Initialize Gemini Client (Make sure you set ENV variable)
# -------------------------------------------------
# export GEMINI_API_KEY="your_key_here"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# -------------------------------------------------
# Helper: Format history for LLM
# -------------------------------------------------
def convert_history_for_prompt(history: List[Dict]) -> str:
    lines = []
    for entry in history:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
        lines.append(f"- [{ts}] {entry['request']}")
    return "\n".join(lines)


# -------------------------------------------------
# MAIN FUNCTION:
# Send history → Get PRIORITIZED tasks + AI INSIGHTS
# -------------------------------------------------
def get_ai_prioritized_tasks(history: List[Dict]):
    """
    Sends patient request history to Gemini LLM.
    Returns: {
        "prioritized_tasks": [...],
        "ai_insights": [...],
        "wellbeing_summary": {...}
    }
    """

    if not history:
        return {
            "prioritized_tasks": [],
            "ai_insights": ["No requests in history"],
            "wellbeing_summary": {
                "score": "0/10",
                "pain_trend": "Unknown",
                "mobility": "Unknown",
                "hydration": "Unknown"
            }
        }

    history_text = convert_history_for_prompt(history)

    prompt = f"""
You are an AI triage assistant for patient monitoring.

Given the following request history (each has a timestamp):
{history_text}

Your tasks:
1. Analyze urgency based on type:
   - Emergency → highest
   - Bathroom → high
   - Water/Food → medium
   - Blanket/Comfort → low

2. Consider timestamp recency:
   - More recent = higher priority
   - Extremely old request = lower priority

3. Output JSON ONLY in this format:
{{
  "prioritized_tasks": [
      {{"task": "...", "urgency": "high/medium/low", "ai_score": number}},
      ...
  ],
  "ai_insights": [
      "insight 1",
      "insight 2"
  ],
  "wellbeing_summary": {{
      "score": "X/10",
      "pain_trend": "...",
      "mobility": "...",
      "hydration": "..."
  }}
}}

Rules:
- Sort tasks highest → lowest priority using your reasoning.
- Use ai_score to reflect combined urgency + recency.
- KEEP JSON VALID.
"""

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=500
        )
    )

    # Extract valid JSON block from LLM response
    raw = response.text.strip()

    try:
        return json.loads(raw)
    except Exception:
        # fallback if model adds text before JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
