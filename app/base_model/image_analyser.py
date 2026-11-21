from pydantic import BaseModel, ConfigDict, Field

class ImageAnalysis(BaseModel):
    # extra="forbid" -> additionalProperties: false, required by strict mode.
    # Keep every field required and the schema flat (no nested models / $ref).
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="One or two sentence description of the image")
    tags: list[str] = Field(description="Short lowercase keywords")
    objects: list[str] = Field(description="Distinct objects visible in the image")
    visible_text: str = Field(description="Any text read from the image, empty string if none")
    people_count: int = Field(description="Number of people visible")