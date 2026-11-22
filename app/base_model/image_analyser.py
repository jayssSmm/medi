from typing import Literal

from pydantic import BaseModel, ConfigDict

DISCLAIMER = (
    "Automated transcription of a handwritten/printed document and may contain "
    "errors. Always confirm medicine names and doses with the prescribing doctor "
    "or a pharmacist before use."
)


class Medicine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str                 # exactly as written (brand or generic)
    name_confidence: Literal["high", "medium", "low"]
    strength: str             # e.g. "500 mg"
    form: str                 # tablet, capsule, syrup, injection...
    dosage: str               # amount per intake, e.g. "1 tablet", "5 ml"
    frequency: str            # plain English, e.g. "twice daily (morning, night)"
    frequency_as_written: str  # e.g. "1-0-1", "BD", "TDS"
    duration: str             # e.g. "5 days"
    route: str                # oral, topical, IV...
    instructions: str         # "after food", "at bedtime", etc.
    legible: bool             # False if you had to struggle to read this line


class PrescriptionExtraction(BaseModel):
    """What the LLM must return. No defaults: strict mode needs every field required."""
    model_config = ConfigDict(extra="forbid")

    is_prescription: bool
    document_type: Literal["handwritten", "printed", "mixed", "unknown"]
    patient_name: str
    patient_age: str
    patient_gender: str
    doctor_name: str
    doctor_registration_no: str
    clinic_or_hospital: str
    date: str
    diagnosis_or_complaints: str
    medicines: list[Medicine]
    tests_advised: list[str]
    general_instructions: list[str]   # diet, rest, avoid X, etc.
    follow_up: str
    unreadable_parts: list[str]       # describe what could not be read
    warnings: list[str]               # ambiguities worth double-checking
    raw_text: str                     # best-effort full transcription


class PrescriptionResponse(PrescriptionExtraction):
    disclaimer: str = DISCLAIMER