# app/clients/llm_client.py
import os
import json
import asyncio
from typing import Tuple, Dict, Any

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- Mock Fallback ---
def _mock_classify_text(content: str) -> Tuple[str, float, str, Dict[str, Any]]:
    toxic_words = ["dumb", "idiot", "hate"]
    if any(w in content.lower() for w in toxic_words):
        return "toxic", 0.95, "Detected offensive language", {"mock": True}
    return "safe", 0.99, "No harmful content detected", {"mock": True}

def _mock_classify_image(image_url: str) -> Tuple[str, float, str, Dict[str, Any]]:
    if "nsfw" in image_url.lower() or "porn" in image_url.lower():
        return "toxic", 0.95, "Detected inappropriate image content", {"mock": True}
    return "safe", 0.99, "No harmful content detected", {"mock": True}

# --- Gemini (Text) ---
async def _gemini_classify_text(content: str):
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        "Classify the following user content into one of: toxic, spam, harassment, safe. "
        "Return JSON strictly in this format: "
        '{"classification":"...", "confidence":0-1, "reasoning":"..."}\n\n'
        f"Content:\n{content}"
    )

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: model.generate_content(prompt)
    )

    text = response.text.strip()
    try:
        parsed = json.loads(text)
        return (
            parsed.get("classification", "safe"),
            float(parsed.get("confidence", 0.9)),
            parsed.get("reasoning", ""),
            {"gemini": parsed},
        )
    except Exception:
        return "safe", 0.9, text, {"gemini_raw": text}

# --- Gemini (Image) ---
async def _gemini_classify_image(image_url: str):
    # 🚧 Currently mock-based — Gemini Vision can be integrated if needed
    return _mock_classify_image(image_url)

# --- Public wrappers (sync for services) ---
def classify_text(content: str):
    if GEMINI_KEY:
        return asyncio.run(_gemini_classify_text(content))
    return _mock_classify_text(content)

def classify_image(image_url: str):
    if GEMINI_KEY:
        return asyncio.run(_gemini_classify_image(image_url))
    return _mock_classify_image(image_url)
