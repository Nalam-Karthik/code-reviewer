# flask-api/app/services/ai.py

import os
import json
import requests
import logging

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"


def get_code_review(language: str, code: str, past_reviews: list = None) -> dict:
    """
    Send code to OpenRouter and return a structured review dict.

    past_reviews: list of similar past reviews from ChromaDB.
    If provided, they're injected into the system prompt so the AI
    can reference the user's recurring patterns.
    """

    # ── Build memory context block ─────────────────────────
    # If we have past reviews, tell the AI about them
    memory_context = ""
    if past_reviews:
        memory_context = "\n\nContext from this user's past reviews (similar code):\n"
        for i, r in enumerate(past_reviews[:3], 1):
            memory_context += f"\nPast review {i} (score: {r.get('score')}):\n"
            memory_context += r.get("summary", "")[:300]  # truncate long summaries
        memory_context += "\n\nUse the above context to identify recurring issues."

    system_prompt = f"""You are an expert code reviewer.{memory_context}
Analyze the submitted code and respond ONLY with a valid JSON object.
No explanation outside the JSON. The JSON must have exactly this shape:
{{
  "summary": "one sentence overall assessment",
  "score": <integer 0-100 where 100 is perfect>,
  "issues": [
    {{
      "line": <line number or null>,
      "severity": "error" | "warning" | "suggestion",
      "message": "what the problem is",
      "fix": "how to fix it"
    }}
  ],
  "strengths": ["thing done well"],
  "recurring_issues": ["issues seen in past reviews too, or empty list"],
  "language_detected": "language name"
}}"""

    user_prompt = f"Language: {language}\n\nCode:\n```{language}\n{code}\n```"

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "http://localhost:5001",
                "X-Title":       "Code Reviewer"
            },
            json={
                "model":    OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                "temperature": 0.2,
            },
            timeout=30
        )
        response.raise_for_status()

        data        = response.json()
        raw_content = data["choices"][0]["message"]["content"].strip()
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        # Strip markdown code fences if the AI wrapped JSON in ```json
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]

        review = json.loads(raw_content.strip())
        return {"review": review, "tokens_used": tokens_used, "error": None}

    except json.JSONDecodeError:
        return {
            "review": {
                "summary": raw_content, "score": None,
                "issues": [], "strengths": [], "recurring_issues": []
            },
            "tokens_used": 0,
            "error": "AI returned non-JSON response"
        }
    except Exception as e:
        return {"review": None, "tokens_used": 0, "error": str(e)}