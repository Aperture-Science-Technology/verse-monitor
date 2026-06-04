"""Pydantic models for tool outputs."""

from pydantic import BaseModel, Field
from typing import List, Optional


class RagSource(BaseModel):
    label: str = Field(..., description="Source label")
    url: str = Field(..., description="Source URL")


class RagResult(BaseModel):
    answer: str = Field(..., description="Generated answer")
    sources: List[RagSource] = Field(default_factory=list, description="List of sources")
    patch_version: Optional[str] = Field(None, description="Patch version if applicable")


class ShipStatsOutput(BaseModel):
    name: str = Field(..., description="Ship name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer")
    role: Optional[str] = Field(None, description="Role (e.g., Fighter, Freighter)")
    size: Optional[str] = Field(None, description="Size")
    length: Optional[float] = Field(None, description="Length in meters")
    beam: Optional[float] = Field(None, description="Beam in meters")
    height: Optional[float] = Field(None, description="Height in meters")
    mass: Optional[float] = Field(None, description="Mass in kg")
    cargo_capacity: Optional[float] = Field(None, description="Cargo capacity in SCU")
    max_speed: Optional[float] = Field(None, description="Max speed in m/s")
    scm_speed: Optional[float] = Field(None, description="SCM speed in m/s")
    afterburner_speed: Optional[float] = Field(None, description="Afterburner speed in m/s")
    min_crew: Optional[int] = Field(None, description="Minimum crew")
    max_crew: Optional[int] = Field(None, description="Maximum crew")
    weapon_size: Optional[str] = Field(None, description="Weapon size")
    shield_size: Optional[str] = Field(None, description="Shield size")
    armor_size: Optional[str] = Field(None, description="Armor size")
    description: Optional[str] = Field(None, description="Description")


class CompareShipsOutput(BaseModel):
    ship_a: ShipStatsOutput
    ship_b: ShipStatsOutput
    comparison: str = Field(..., description="Comparison summary")


class GuideOutput(BaseModel):
    title: str = Field(..., description="Guide title")
    steps: List[str] = Field(..., description="Step-by-step instructions")
    player_level: str = Field(..., description="Player level")
    tips: Optional[List[str]] = Field(None, description="Additional tips")


class LoreResult(BaseModel):
    title: str = Field(..., description="Lore entry title")
    content: str = Field(..., description="Lore content")
    url: str = Field(..., description="Source URL")
    related_topics: List[str] = Field(default_factory=list, description="Related lore topics")


class SearchLoreOutput(BaseModel):
    results: List[LoreResult] = Field(..., description="Search results")