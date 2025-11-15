import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

# Configure the correct Gemini SDK
genai.configure(api_key=API_KEY)

MODEL_NAME = "models/gemini-2.5-flash"

def get_ai_prioritized_tasks(history):
    if not history:
        return {
            "prioritized_tasks": [],
            "ai_insights": ["No patient requests yet."],
            "wellbeing_summary": {}
        }

    formatted_history = "\n".join(
        f"- {item['request']} at {item['timestamp']}"
        for item in history[-10:]
    )

    prompt = f"""
You are an AI assistant analyzing patient requests.

Patient request history:
{formatted_history}

Tasks:
1. Prioritize these patient needs.
2. Provide 2–3 insights.
3. Give a wellbeing score (0-10).

Respond in JSON ONLY:
{{
  "prioritized_tasks": [...],
  "ai_insights": [...],
  "wellbeing_summary": {{}}
}}
"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )


        text = response.text
        print("gemini responded ", json.loads(text))

        try:
            return json.loads(text)
        except:
            import re
            match = re.search(r"\{(.|\n)*\}", text)
            if match:
                return json.loads(match.group(0))

            raise ValueError("Invalid AI JSON output")

    except Exception as e:
        print("⚠️ Gemini API failed:", e)
        return {
            "prioritized_tasks": [],
            "ai_insights": ["AI offline – fallback mode", str(e)],
            "wellbeing_summary": {"score": "N/A"}
        }
