"""Item request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)


class ItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)


class ItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    description: str
    created_at: datetime
