# For now, use a simple mock
# Later, integrate OpenAI/Gemini properly

def classify_text(content: str):
    if any(word in content.lower() for word in ["dumb", "idiot", "hate"]):
        return "toxic", 0.95, "Detected offensive language", {"mock": True}
    return "safe", 0.99, "No harmful content detected", {"mock": True}
