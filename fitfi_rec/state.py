"""LangGraph state schema.

`State` is a TypedDict (`total=False`) so each node can fill in only the
fields it produces. LangGraph merges partial dicts back into state.
"""

from typing import TypedDict, Optional
from .types import (
    QuizAnswers,
    Product,
    ColorProfile,
    ArchetypeProfile,
    OutfitSlot,
    Outfit,
    RankedOutfit,
)


class State(TypedDict, total=False):
    quiz: QuizAnswers
    products: list[Product]
    color_profile: Optional[ColorProfile]

    archetype: ArchetypeProfile
    filtered_products: list[Product]
    classified: dict[OutfitSlot, list[Product]]
    candidates: list[Outfit]
    ranked: list[RankedOutfit]
    final: list[RankedOutfit]
