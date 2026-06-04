"""Pydantic models for tool inputs."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class AskInput(BaseModel):
    question: str = Field(..., description="The question to ask about Star Citizen")
    category: Optional[str] = Field(None, description="Optional category to filter results")
    system_prompt: Optional[str] = Field("", description="Optional system prompt to guide the answer")
    top_k: Optional[int] = Field(5, description="Number of chunks to retrieve")


class GetShipStatsInput(BaseModel):
    ship_name: str = Field(..., description="Name of the ship to get stats for")


class CompareShipsInput(BaseModel):
    ship_a: str = Field(..., description="First ship name")
    ship_b: str = Field(..., description="Second ship name")


class GetGuideInput(BaseModel):
    guide_title: str = Field(..., description="Title of the guide to retrieve")
    player_level: Literal["beginner", "intermediate", "advanced"] = Field(
        "beginner", description="Player level for the guide"
    )


class SearchLoreInput(BaseModel):
    query: str = Field(..., description="Search query for lore")
    top_k: Optional[int] = Field(5, description="Number of results to return")