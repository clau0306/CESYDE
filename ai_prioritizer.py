import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import re
import time # Import time for timestamp formatting

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

genai.configure(api_key=API_KEY)

# Use a more recent model if available, otherwise fallback
MODEL_NAME = "models/gemini-1.5-flash" 

def get_ai_prioritized_tasks(history):
    if not history:
        return {
            "prioritized_tasks": [],
            "ai_insights": ["No patient requests yet. System is idle."],
            "wellbeing_summary": {"score": 10, "rationale": "No requests indicates the patient is currently stable."}
        }

    # Format timestamps to be human-readable for the AI
    formatted_history = "\n".join(
        f"- {item['request']} at {time.strftime('%I:%M:%S %p', time.localtime(item['timestamp']))}"
        for item in history[-10:]
    )

    # --- THIS IS THE UPDATED PROMPT ---
    # It is now very specific about the JSON output format
    # to match exactly what main.html expects.
    prompt = f"""
You are a brilliant hospital nurse AI assistant. Your job is to analyze a list of recent patient requests and provide actionable, prioritized tasks for the nursing staff.

Here is the recent request history from the patient (last 10 requests):
{formatted_history}

Based *only* on this history, perform the following tasks:
1.  **Prioritize Tasks:** Generate a list of critical tasks for the nurse.
2.  **Generate Insights:** Provide 2-3 brief insights about the patient's potential state.
3.  **Wellbeing Score:** Provide an overall patient wellbeing score from 0 (Critical) to 10 (Stable), and a brief rationale.

Respond in this exact JSON format. Do not include any other text or markdown:
{{
  "prioritized_tasks": [
    {{
      "request_type": "The specific task, e.g., 'Address Bathroom Request' or 'Check on Patient'",
      "priority": "High | Medium | Low"
    }}
  ],
  "ai_insights": [
    "Your first insight here.",
    "Your second insight here."
  ],
  "wellbeing_summary": {{
    "score": 8,
    "rationale": "Your brief rationale for the score here."
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
        print("gemini responded ", text) # Log the raw text
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: Try to find JSON within markdown
            match = re.search(r"```json\n(\{.*?\})\n```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            print("⚠️ Gemini API returned invalid JSON")
            raise ValueError("Invalid AI JSON output")

    except Exception as e:
        print(f"⚠️ Gemini API failed: {e}")
        return {
            "prioritized_tasks": [{"request_type": "AI is offline. Check requests manually.", "priority": "High"}],
            "ai_insights": [f"Error connecting to AI: {e}"],
            "wellbeing_summary": {"score": "N/A", "rationale": "AI system is offline."}
        }