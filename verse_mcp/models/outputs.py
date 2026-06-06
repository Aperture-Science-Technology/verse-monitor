"""Pydantic models for tool outputs."""

from typing import Optional
from pydantic import BaseModel, Field


class RagSource(BaseModel):
    label: str = Field(..., description="Source label")
    url: str = Field(..., description="Source URL")


class RagResult(BaseModel):
    answer: str = Field(..., description="Formatted answer with source context chunks")
    sources: list[RagSource] = Field(default_factory=list, description="Sources cited in the answer")
    patch_version: Optional[str] = Field(None, description="Most recent patch version referenced")


class LoreResult(BaseModel):
    title: str = Field(..., description="Lore entry title or source label")
    content: str = Field(..., description="Lore entry content")
    url: str = Field(..., description="Source URL")
    related_topics: list[str] = Field(default_factory=list, description="Related lore topics")


class SearchLoreOutput(BaseModel):
    results: list[LoreResult] = Field(..., description="List of lore search results")


class GuideOutput(BaseModel):
    title: str = Field(..., description="Guide title")
    steps: list[str] = Field(..., description="Step-by-step instructions (one context chunk per step)")
    player_level: str = Field(..., description="Target player level (beginner/intermediate/advanced)")
    tips: Optional[list[str]] = Field(None, description="Additional tips")


class ShipStatsOutput(BaseModel):
    ship_name: str = Field(..., description="Ship name")
    description: str = Field(..., description="Technical specifications and statistics from knowledge base")
    manufacturer: Optional[str] = Field(None, description="Ship manufacturer")
    role: Optional[str] = Field(None, description="Ship role/category")
    crew_min: Optional[int] = Field(None, description="Minimum crew size")
    crew_max: Optional[int] = Field(None, description="Maximum crew size")
    cargo_capacity: Optional[str] = Field(None, description="Cargo capacity in SCU")
    price_auec: Optional[str] = Field(None, description="In-game price in aUEC")
