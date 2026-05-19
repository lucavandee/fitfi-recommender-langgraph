"""Node functions for the recommender graph.

Each node accepts the current state, computes one thing, and returns a
partial state dict that LangGraph merges back in.
"""

from collections import defaultdict
from itertools import product as cartesian_product
from .state import State
from .types import (
    Archetype,
    ArchetypeProfile,
    Gender,
    OutfitSlot,
    Outfit,
    Product,
    RankedOutfit,
)


_STYLE_TO_ARCHETYPE: dict[str, dict[Archetype, float]] = {
    "minimalist": {Archetype.MINIMALIST: 1.0},
    "classic": {Archetype.FORMAL: 0.8, Archetype.MINIMALIST: 0.2},
    "casual": {Archetype.CASUAL: 1.0},
    "sporty": {Archetype.SPORTY: 1.0},
    "vintage": {Archetype.VINTAGE: 1.0},
    "romantic": {Archetype.VINTAGE: 0.5, Archetype.FORMAL: 0.3, Archetype.CASUAL: 0.2},
    "edgy": {Archetype.SPORTY: 0.4, Archetype.VINTAGE: 0.4, Archetype.MINIMALIST: 0.2},
}

_OCCASION_BOOSTS: dict[str, dict[Archetype, float]] = {
    "work": {Archetype.FORMAL: 2.0},
    "office": {Archetype.FORMAL: 2.0},
    "sport": {Archetype.SPORTY: 2.5},
    "wedding": {Archetype.FORMAL: 2.0},
    "casual": {Archetype.CASUAL: 1.5},
    "everyday": {Archetype.CASUAL: 1.0},
}


def derive_archetype(state: State) -> dict:
    """Map quiz answers to a dominant + secondary archetype with mix factor."""
    quiz = state["quiz"]
    scores: dict[Archetype, float] = defaultdict(float)

    for selection in quiz.style_selections:
        for arch, w in _STYLE_TO_ARCHETYPE.get(selection.lower(), {}).items():
            scores[arch] += w

    for occasion in quiz.occasions:
        for arch, b in _OCCASION_BOOSTS.get(occasion.lower(), {}).items():
            scores[arch] += b

    if not scores:
        scores[Archetype.CASUAL] = 1.0

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_scores[0][0]
    secondary = sorted_scores[1][0] if len(sorted_scores) > 1 else dominant

    total = sum(scores.values())
    mix = scores[secondary] / total if total > 0 else 0.0

    profile = ArchetypeProfile(
        dominant=dominant,
        secondary=secondary,
        mix_factor=min(mix, 0.5),
        scores=dict(scores),
    )
    return {"archetype": profile}


def filter_products(state: State) -> dict:
    """Hard filters: budget, gender, stock."""
    quiz = state["quiz"]
    filtered = [
        p
        for p in state["products"]
        if p.in_stock
        and (p.gender == quiz.gender or p.gender == Gender.UNISEX)
        and p.price <= quiz.budget_max
    ]
    return {"filtered_products": filtered}


def reclassify(state: State) -> dict:
    """Group filtered products by outfit slot."""
    grouped: dict[OutfitSlot, list[Product]] = defaultdict(list)
    for p in state["filtered_products"]:
        grouped[p.slot].append(p)
    return {"classified": dict(grouped)}


def photo_enhance(state: State) -> dict:
    """Boost archetype weights of color-compatible items.

    Runs only when a `color_profile` is in state. Returns a fresh
    classified dict with boosted product copies; originals untouched.
    """
    color_profile = state["color_profile"]
    compatible = {c.lower() for c in color_profile.compatible_colors}

    boosted: dict[OutfitSlot, list[Product]] = {}
    for slot, items in state["classified"].items():
        boosted_items = []
        for p in items:
            if any(c.lower() in compatible for c in p.colors):
                new_weights = {a: w * 1.2 for a, w in p.archetype_weights.items()}
                boosted_items.append(p.model_copy(update={"archetype_weights": new_weights}))
            else:
                boosted_items.append(p)
        boosted[slot] = boosted_items
    return {"classified": boosted}


def _take_top_n(items: list[Product], archetype: Archetype, n: int) -> list[Product]:
    return sorted(
        items,
        key=lambda p: p.archetype_weights.get(archetype, 0.0),
        reverse=True,
    )[:n]


def assemble(state: State) -> dict:
    """Build outfit candidates by combining top-N products per slot."""
    classified = state["classified"]
    profile = state["archetype"]

    n_per_slot = 3
    top_tops = _take_top_n(classified.get(OutfitSlot.TOP, []), profile.dominant, n_per_slot)
    top_bottoms = _take_top_n(classified.get(OutfitSlot.BOTTOM, []), profile.dominant, n_per_slot)
    top_shoes = _take_top_n(classified.get(OutfitSlot.SHOES, []), profile.dominant, n_per_slot)

    candidates = [
        Outfit(items={OutfitSlot.TOP: t, OutfitSlot.BOTTOM: b, OutfitSlot.SHOES: s})
        for t, b, s in cartesian_product(top_tops, top_bottoms, top_shoes)
    ]
    return {"candidates": candidates}


def rank(state: State) -> dict:
    """Score each outfit by archetype match, blended by mix_factor."""
    profile = state["archetype"]
    ranked: list[RankedOutfit] = []

    for outfit in state["candidates"]:
        dom_match = sum(p.archetype_weights.get(profile.dominant, 0.0) for p in outfit.items.values())
        sec_match = sum(p.archetype_weights.get(profile.secondary, 0.0) for p in outfit.items.values())
        score = dom_match * (1 - profile.mix_factor) + sec_match * profile.mix_factor
        reasons = [
            f"{profile.dominant.value} match: {dom_match:.2f}",
            f"{profile.secondary.value} match: {sec_match:.2f}",
            f"mix factor: {profile.mix_factor:.2f}",
        ]
        ranked.append(RankedOutfit(outfit=outfit, score=score, reasons=reasons))

    ranked.sort(key=lambda x: x.score, reverse=True)
    return {"ranked": ranked}


def diversity(state: State) -> dict:
    """Drop near-duplicate outfits sharing the same brand signature; keep top 5."""
    seen: set[tuple] = set()
    final: list[RankedOutfit] = []
    for r in state["ranked"]:
        sig = tuple(sorted(p.brand for p in r.outfit.items.values()))
        if sig in seen:
            continue
        seen.add(sig)
        final.append(r)
        if len(final) >= 5:
            break
    return {"final": final}


def needs_photo_enhance(state: State) -> str:
    """Conditional edge predicate: route to photo_enhance only if color_profile present."""
    return "photo_enhance" if state.get("color_profile") else "assemble"
