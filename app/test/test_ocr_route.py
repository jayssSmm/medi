# test_prescriptions.py  (place in the project root, next to the `app/` folder)
import json
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # must run BEFORE importing the router: it raises if GROQ_API_KEY is missing

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.prescription_ocr import router

FOLDER = Path(__file__).resolve().parent.parent / "prescriptions"  
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

app = FastAPI()
app.include_router(router)  # add prefix="/api" here if you use one in your real app


def main() -> None:
    images = sorted(p for p in FOLDER.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        sys.exit(f"No images found in {FOLDER}")

    # Using the client as a context manager keeps one event loop alive for all
    # requests, which avoids "Event loop is closed" errors with the module-level AsyncGroq client.
    with TestClient(app) as client:
        for img in images:
            mime = mimetypes.guess_type(img.name)[0] or "image/jpeg"
            print("=" * 70)
            print(f"File: {img.name}  ({mime})")
            print("=" * 70)

            with img.open("rb") as f:
                resp = client.post(
                    "/analyze-prescription",
                    files={"file": (img.name, f, mime)},
                )

            print(f"Status: {resp.status_code}")
            try:
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            except ValueError:
                print(resp.text)
            print()


if __name__ == "__main__":
    main()