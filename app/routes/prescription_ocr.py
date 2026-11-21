import base64
import os

import groq
from fastapi import APIRouter, File, HTTPException, UploadFile
from groq import AsyncGroq
from app.base_model.image_analyser import ImageAnalysis

GROQ_MODEL = "qwen/qwen3.8-27b"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 4 * 1024 * 1024  # conservative cap for base64 uploads

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is not set")

client = AsyncGroq(api_key=api_key)
router = APIRouter()


SYSTEM_PROMPT = (
    "You analyze images. Respond only with JSON that matches the provided schema. "
    "Do not guess: use an empty string or empty list when something is not present."
)


@router.post("/analyze-image", response_model=ImageAnalysis)
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 4 MB)")

    b64 = base64.b64encode(data).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"

    try:
        completion = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "image_analysis",
                    "strict": True,
                    "schema": ImageAnalysis.model_json_schema(),
                },
            },
            temperature=0.2,
            max_completion_tokens=1024,
        )
    except groq.APIStatusError as e:
        raise HTTPException(502, f"Groq API error ({e.status_code}): {e.message}")
    except groq.APIConnectionError:
        raise HTTPException(503, "Could not reach Groq API")

    content = completion.choices[0].message.content
    try:
        return ImageAnalysis.model_validate_json(content)
    except Exception:
        raise HTTPException(502, "Model returned invalid JSON")