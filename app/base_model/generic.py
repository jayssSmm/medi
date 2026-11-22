# app/base_model/generic_lookup.py
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenericMatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drug_code: str = ""
    generic_name: str = ""
    unit_size: str = ""
    mrp: str = ""
    group_name: str = ""


class MedicineResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    strength: str
    form: str
    match_status: Literal["exact_match", "partial_match", "uncertain", "not_found"]
    matches: list[GenericMatch] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GenericLookup(BaseModel):
    results: list[MedicineResult]