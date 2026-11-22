import base64
import io
import os

import groq
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from groq import AsyncGroq
from PIL import Image, ImageOps, UnidentifiedImageError

from app.base_model.image_analyser import PrescriptionExtraction, PrescriptionResponse

from app.system_prompts.orc_prompt import OCR_SYSTEM_PROMPT as SYSTEM_PROMPT

GROQ_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024   # what we accept from the client
MAX_SENT_BYTES = 3_500_000            # what we send to Groq (base64 adds ~33%)
MAX_SIDE = 2048                       # keep enough resolution for handwriting

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is not set")

client = AsyncGroq(api_key=api_key)
router = APIRouter()

def _prepare_image(data: bytes) -> bytes:
    """Fix rotation, downscale and re-encode as JPEG so the base64 payload stays small."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # phone photos are often rotated via EXIF
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    for quality in (90, 80, 70, 60):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= MAX_SENT_BYTES:
            return buf.getvalue()
    raise ValueError("Image could not be compressed enough")

@router.post("/analyze-prescription", response_model=PrescriptionResponse)
async def analyze_prescription(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large (max 15 MB)")

    try:
        jpeg = await run_in_threadpool(_prepare_image, data)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "File is not a valid image")
    except ValueError as e:
        raise HTTPException(413, str(e))

    data_url = f"data:image/jpeg;base64,{base64.b64encode(jpeg).decode('utf-8')}"

    try:
        completion = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract the details from this prescription."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "prescription_extraction",
                    "strict": True,
                    "schema": PrescriptionExtraction.model_json_schema(),
                },
            },
            temperature=0,
            max_completion_tokens=2048,
        )
    except groq.APIStatusError as e:
        raise HTTPException(502, f"Groq API error ({e.status_code}): {e.message}")
    except groq.APIConnectionError:
        raise HTTPException(503, "Could not reach Groq API")

    content = completion.choices[0].message.content
    try:
        extraction = PrescriptionExtraction.model_validate_json(content)
    except Exception:
        raise HTTPException(502, "Model returned invalid JSON")

    if not extraction.is_prescription:
        raise HTTPException(422, "The image does not appear to be a prescription")

    return PrescriptionResponse(**extraction.model_dump())