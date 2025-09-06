# app/clients/llm_client.py
import os
import json
import asyncio
from typing import Tuple, Dict, Any

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

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

# --- OpenAI GPT-4 (Text) ---
async def _openai_classify_text(content: str):
    import openai
    
    client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
    
    prompt = (
        "Classify the following user content into one of: toxic, spam, harassment, safe. "
        "Return JSON strictly in this format: "
        '{"classification":"...", "confidence":0-1, "reasoning":"..."}\n\n'
        f"Content:\n{content}"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a content moderation AI. Analyze text and classify it as toxic, spam, harassment, or safe."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        text = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(text)
            return (
                parsed.get("classification", "safe"),
                float(parsed.get("confidence", 0.9)),
                parsed.get("reasoning", ""),
                {"openai": parsed},
            )
        except Exception:
            return "safe", 0.9, text, {"openai_raw": text}
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return "safe", 0.9, f"OpenAI API error: {str(e)}", {"openai_error": str(e)}

# --- OpenAI GPT-4 Vision (Image) ---
async def _openai_classify_image(image_url: str):
    import openai
    
    client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
    
    prompt = (
        "Analyze this image for inappropriate content. Classify it as: toxic, spam, harassment, or safe. "
        "Return JSON strictly in this format: "
        '{"classification":"...", "confidence":0-1, "reasoning":"..."}'
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        text = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(text)
            return (
                parsed.get("classification", "safe"),
                float(parsed.get("confidence", 0.9)),
                parsed.get("reasoning", ""),
                {"openai": parsed},
            )
        except Exception:
            return "safe", 0.9, text, {"openai_raw": text}
    except Exception as e:
        print(f"OpenAI Vision API error: {str(e)}")
        return "safe", 0.9, f"OpenAI Vision API error: {str(e)}", {"openai_error": str(e)}

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
    if OPENAI_KEY:
        return asyncio.run(_openai_classify_text(content))
    elif GEMINI_KEY:
        return asyncio.run(_gemini_classify_text(content))
    return _mock_classify_text(content)

def classify_image(image_url: str):
    if OPENAI_KEY:
        return asyncio.run(_openai_classify_image(image_url))
    elif GEMINI_KEY:
        return asyncio.run(_gemini_classify_image(image_url))
    return _mock_classify_image(image_url)
