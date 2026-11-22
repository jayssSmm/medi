# app/test/test_generic_lookup.py
# Run from the project root:  python -m app.test.test_generic_lookup [optional_input.json]
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")  # before importing anything that reads env vars

from app.base_model.generic import GenericLookup
from app.base_model.image_analyser import PrescriptionExtraction

# Adjust these two imports to wherever your graph and tools actually live
from app.business.graph import get_graph
from app.business.rag_tools import tool_node
from app.business.run_agent import ask

DEFAULT_INPUT = {
    "is_prescription": True,
    "document_type": "handwritten",
    "patient_name": "Mr. Sachin Sansare",
    "patient_age": "28",
    "patient_gender": "male",
    "doctor_name": "Dr. Amit",
    "doctor_registration_no": "",
    "clinic_or_hospital": "THE WHITE TUSK",
    "date": "12/10/22",
    "diagnosis_or_complaints": "",
    "medicines": [
        {
            "name": "Augmentin", "name_confidence": "high", "strength": "625mg",
            "form": "tablet", "dosage": "1 tablet", "frequency": "morning and night",
            "frequency_as_written": "1-0-1", "duration": "5 days", "route": "oral",
            "instructions": "after meals", "legible": True,
        },
        {
            "name": "Enzylam", "name_confidence": "medium", "strength": "",
            "form": "tablet", "dosage": "1 tablet", "frequency": "morning and night",
            "frequency_as_written": "1-0-1", "duration": "5 days", "route": "oral",
            "instructions": "after meals", "legible": True,
        },
        {
            "name": "Pan D", "name_confidence": "high", "strength": "40mg",
            "form": "tablet", "dosage": "1 tablet", "frequency": "morning only",
            "frequency_as_written": "1-0-0", "duration": "5 days", "route": "oral",
            "instructions": "before meals", "legible": True,
        },
    ],
    "tests_advised": [],
    "general_instructions": ["Hexigel gum paint massage 1-0-1 x 1 week"],
    "follow_up": "",
    "unreadable_parts": [],
    "warnings": [
        "Enzylam is a brand name; the exact generic composition is not specified on the prescription."
    ],
    "raw_text": (
        "THE WHITE TUSK\nSmile Designing | Teeth Whitening\nDental Implants | General Dentistry\n"
        "@/whitetusk dental\n\n12/10/22\nMr. Sachin Sansare\n28/M\n\nRx,\n\n"
        "after meals { Tab. Augmentin 625mg\n              1-0-1 x 5 days\n"
        "              Tab. Enzylam\n              1-0-1 x 5 days\n\n"
        "before meals { Tab. Pan D 40mg\n               1-0-0 x 5 days\n\n"
        "Adv: Hexigel gum paint\n      massage\n      1-0-1 x 1 week\n\n[signature] Amit\n\n"
        "Ph: +91 8108123211 | Web: www.thewhitetusk.com | Email: info@thewhitetusk.com"
    ),
    "disclaimer": "Automated transcription ... confirm with a pharmacist.",
}


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def part1_load_input() -> PrescriptionExtraction:
    banner("PART 1: load and validate input")
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        print(f"Using input from {sys.argv[1]}")
    else:
        data = dict(DEFAULT_INPUT)
        print("Using built-in default input")

    data.pop("disclaimer", None)  # response-only field; extra="forbid" would reject it
    extraction = PrescriptionExtraction.model_validate(data)
    print(f"OK: {len(extraction.medicines)} medicine(s): "
          + ", ".join(m.name for m in extraction.medicines))
    return extraction


def part2_run_agent(extraction: PrescriptionExtraction) -> GenericLookup:
    banner("PART 2: run agent")
    graph = get_graph(tool_node)
    lookup = ask(graph, extraction.medicines, debug=False)  # set debug=True to see the tool-call trace
    print("Agent finished.")
    return lookup


def part3_check_structure(extraction: PrescriptionExtraction, lookup: GenericLookup) -> bool:
    banner("PART 3: structural checks")
    ok = True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + msg)
        ok = ok and cond

    meds = extraction.medicines
    check(len(lookup.results) == len(meds), f"one result per medicine ({len(lookup.results)}/{len(meds)})")

    for m, r in zip(meds, lookup.results):
        check((r.name, r.strength, r.form) == (m.name, m.strength, m.form),
              f"[{m.name}] input echoed unchanged")
        check(all(x.drug_code and x.generic_name for x in r.matches),
              f"[{m.name}] every match has drug_code and generic_name")
        check(len(r.matches) <= 3, f"[{m.name}] at most 3 matches")
        if r.match_status == "not_found":
            check(r.matches == [], f"[{m.name}] not_found has no matches")
        else:
            check(len(r.matches) > 0, f"[{m.name}] {r.match_status} has at least one match")
        if any("Lookup failed" in n for n in r.notes):
            check(False, f"[{m.name}] agent lookup failed: {r.notes}")
    return ok


def part4_print(lookup: GenericLookup) -> None:
    banner("PART 4: result")
    print(lookup.model_dump_json(indent=2))

    banner("SUMMARY")
    for r in lookup.results:
        print(f"{r.name} {r.strength} {r.form}".strip() + f"  ->  {r.match_status}")
        for x in r.matches:
            print(f"    {x.drug_code} | {x.generic_name} | {x.unit_size} | MRP {x.mrp} | {x.group_name}")
        for n in r.notes:
            print(f"    note: {n}")


def main() -> None:
    extraction = part1_load_input()
    lookup = part2_run_agent(extraction)
    passed = part3_check_structure(extraction, lookup)
    part4_print(lookup)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()