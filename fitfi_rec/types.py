"""Pydantic domain models.

These mirror the shapes of the TypeScript recommendation engine but are
intentionally smaller in scope than the production schema.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Archetype(str, Enum):
    CASUAL = "casual"
    FORMAL = "formal"
    SPORTY = "sporty"
    VINTAGE = "vintage"
    MINIMALIST = "minimalist"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNISEX = "unisex"


class OutfitSlot(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    SHOES = "shoes"
    DRESS = "dress"


class Product(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    gender: Gender
    slot: OutfitSlot
    colors: list[str]
    tags: list[str] = Field(default_factory=list)
    archetype_weights: dict[Archetype, float] = Field(default_factory=dict)
    in_stock: bool = True


class QuizAnswers(BaseModel):
    gender: Gender
    budget_max: float = 200.0
    occasions: list[str] = Field(default_factory=list)
    style_selections: list[str] = Field(default_factory=list)
    season: Optional[str] = None


class ColorProfile(BaseModel):
    """Optional output of selfie color analysis."""
    season: str
    compatible_colors: list[str]


class ArchetypeProfile(BaseModel):
    dominant: Archetype
    secondary: Archetype
    mix_factor: float = Field(ge=0.0, le=1.0)
    scores: dict[Archetype, float]


class Outfit(BaseModel):
    items: dict[OutfitSlot, Product]

    @property
    def total_price(self) -> float:
        return sum(item.price for item in self.items.values())


class RankedOutfit(BaseModel):
    outfit: Outfit
    score: float
    reasons: list[str] = Field(default_factory=list)
