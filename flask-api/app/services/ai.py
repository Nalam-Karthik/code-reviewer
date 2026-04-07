# flask-api/app/services/ai.py

import os
import requests
import json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"


def get_code_review(language: str, code: str) -> dict:
    """
    Send code to OpenRouter and return a structured review dict.

    We use a carefully crafted system prompt that forces the AI to
    return valid JSON — this is "JSON mode" prompting.
    The response shape is the contract between backend and any frontend.
    """

    system_prompt = """You are an expert code reviewer. 
Analyze the submitted code and respond ONLY with a valid JSON object.
No explanation outside the JSON. The JSON must have exactly this shape:
{
  "summary": "one sentence overall assessment",
  "score": <integer 0-100 where 100 is perfect>,
  "issues": [
    {
      "line": <line number or null>,
      "severity": "error" | "warning" | "suggestion",
      "message": "what the problem is",
      "fix": "how to fix it"
    }
  ],
  "strengths": ["thing done well", "..."],
  "language_detected": "language name"
}"""

    user_prompt = f"Language: {language}\n\nCode:\n```{language}\n{code}\n```"

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                # OpenRouter requires these for tracking
                "HTTP-Referer":  "http://localhost:5001",
                "X-Title":       "Code Reviewer"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                "temperature": 0.2,   # low temperature = consistent, structured output
            },
            timeout=30
        )
        response.raise_for_status()

        data         = response.json()
        raw_content  = data["choices"][0]["message"]["content"]
        tokens_used  = data.get("usage", {}).get("total_tokens", 0)

        # Parse the JSON the AI returned
        # strip() removes whitespace, the AI sometimes adds newlines
        review = json.loads(raw_content.strip())
        return {"review": review, "tokens_used": tokens_used, "error": None}

    except json.JSONDecodeError:
        # AI didn't return valid JSON — return raw text as summary
        return {
            "review": {"summary": raw_content, "score": None, "issues": [], "strengths": []},
            "tokens_used": 0,
            "error": "AI returned non-JSON response"
        }
    except Exception as e:
        return {"review": None, "tokens_used": 0, "error": str(e)}