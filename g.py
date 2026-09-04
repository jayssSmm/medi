from dotenv import load_dotenv
from groq import Groq

import base64
import os
import json
import re

load_dotenv()

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

image_path = "ocr2.jpg"
base64_image = encode_image(image_path)

prompt = """You are analyzing a photo of a handwritten doctor's prescription.
Extract every medicine mentioned. For each one, return:
- "raw_text": exactly what you see written
- "best_guess_name": your best guess at the actual medicine name
- "confidence": "high", "medium", or "low"
- "dosage_instructions": if legible, else null
- "alternative_guesses": up to 2 other plausible medicine names it could be

If you cannot confidently read something, say so — do NOT invent a plausible-sounding drug name.
Return ONLY a JSON object with a key "medicines" containing a list of these objects."""

completion = client.chat.completions.create(
    model="qwen/qwen3.6-27b",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]
        }
    ],
    reasoning_effort="none",   # Groq's documented switch to kill thinking mode on qwen3.6
    temperature=0.7,           # Groq's recommended non-thinking-mode value
    top_p=0.80,
    presence_penalty=1.5,      # Groq's recommended non-thinking-mode value — much stronger than before
    max_completion_tokens=2048,
    response_format={"type": "json_object"}
)

raw = completion.choices[0].message.content
result = json.loads(raw)
print(json.dumps(result, indent=2))