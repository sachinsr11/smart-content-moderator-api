def classify_text(content: str):
    """
    Mock text moderation.
    """
    toxic_words = ["dumb", "idiot", "hate"]
    if any(word in content.lower() for word in toxic_words):
        return "toxic", 0.95, "Detected offensive language", {"mock": True}
    return "safe", 0.99, "No harmful content detected", {"mock": True}

def classify_image(image_url: str):
    """
    Mock image moderation.
    """
    if "nsfw" in image_url.lower():
        return "toxic", 0.95, "Detected inappropriate image content", {"mock": True}
    return "safe", 0.99, "No harmful content detected", {"mock": True}
