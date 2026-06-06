"""Pydantic models for tool outputs."""

from pydantic import BaseModel, Field


class RagSource(BaseModel):
    label: str = Field(..., description="Source label")
    url: str = Field(..., description="Source URL")
