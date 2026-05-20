"""Hand-crafted evaluation cases for the recommender graph.

Each case bundles an input (quiz + optional color_profile) with the
expected behavior. The runner in `runner.py` invokes the graph on each
case and scores it against these expectations.
"""

from typing import Optional
from pydantic import BaseModel, Field

from fitfi_rec.types import Archetype, ColorProfile, Gender, QuizAnswers
from fitfi_rec.seed import COLOR_PROFILE_AUTUMN


class EvalCase(BaseModel):
    name: str
    description: str
    quiz: QuizAnswers
    color_profile: Optional[ColorProfile] = None

    expected_dominant: Archetype
    expected_secondary: Optional[Archetype] = None
    min_outfits: int = Field(default=1, ge=1)
    max_item_price: Optional[float] = Field(
        default=None,
        description="If set, every item in every returned outfit must be at or below this price.",
    )
    negative_check: bool = Field(
        default=False,
        description=(
            "If True, the case passes when at least one metric FAILS. Used to prove "
            "the suite actually detects wrong expectations, not just rubber-stamps."
        ),
    )


CASES: list[EvalCase] = [
    EvalCase(
        name="formal_male_basic",
        description=(
            "A male customer indicating work and office occasions plus minimalist and "
            "classic style preferences should receive formal-dominant recommendations."
        ),
        quiz=QuizAnswers(
            gender=Gender.MALE,
            budget_max=600.0,
            occasions=["work", "office"],
            style_selections=["minimalist", "classic"],
            season="autumn",
        ),
        expected_dominant=Archetype.FORMAL,
        expected_secondary=Archetype.MINIMALIST,
        min_outfits=3,
    ),
    EvalCase(
        name="formal_male_with_autumn_palette",
        description=(
            "Same formal male as above, but with an autumn color profile. The "
            "photo_enhance node should execute and surface color-compatible items "
            "(navy, brown, cream) higher in the ranking."
        ),
        quiz=QuizAnswers(
            gender=Gender.MALE,
            budget_max=600.0,
            occasions=["work", "office"],
            style_selections=["minimalist", "classic"],
            season="autumn",
        ),
        color_profile=COLOR_PROFILE_AUTUMN,
        expected_dominant=Archetype.FORMAL,
        expected_secondary=Archetype.MINIMALIST,
        min_outfits=3,
    ),
    EvalCase(
        name="sporty_unisex",
        description=(
            "A unisex customer selecting sport occasion and sporty + casual style "
            "should receive sporty-dominant recommendations with casual as secondary."
        ),
        quiz=QuizAnswers(
            gender=Gender.UNISEX,
            budget_max=300.0,
            occasions=["sport", "casual"],
            style_selections=["sporty", "casual"],
            season="spring",
        ),
        expected_dominant=Archetype.SPORTY,
        expected_secondary=Archetype.CASUAL,
        min_outfits=3,
    ),
    EvalCase(
        name="vintage_unisex",
        description=(
            "A unisex customer selecting vintage style and everyday occasion should "
            "receive vintage-dominant recommendations."
        ),
        quiz=QuizAnswers(
            gender=Gender.UNISEX,
            budget_max=500.0,
            occasions=["everyday"],
            style_selections=["vintage"],
        ),
        expected_dominant=Archetype.VINTAGE,
        min_outfits=3,
    ),
    EvalCase(
        name="budget_constrained_casual",
        description=(
            "A budget-tight unisex customer (max €80 per item) should still get at "
            "least one outfit, and every item in every returned outfit must be ≤ €80."
        ),
        quiz=QuizAnswers(
            gender=Gender.UNISEX,
            budget_max=80.0,
            occasions=["casual"],
            style_selections=["casual"],
        ),
        expected_dominant=Archetype.CASUAL,
        min_outfits=1,
        max_item_price=80.0,
    ),
    EvalCase(
        name="empty_quiz_defaults_to_casual",
        description=(
            "A customer with no style selections and no occasions should default to "
            "casual rather than crashing or returning nothing."
        ),
        quiz=QuizAnswers(gender=Gender.UNISEX, budget_max=300.0),
        expected_dominant=Archetype.CASUAL,
        min_outfits=1,
    ),
    EvalCase(
        name="negative__sporty_input_with_formal_expectation",
        description=(
            "Negative-check case. The quiz signals sport occasions and sporty style "
            "selections, so the graph correctly derives a sporty-dominant archetype. "
            "The case deliberately expects FORMAL, so archetype_dominant_ok must fail. "
            "negative_check=True inverts the pass condition, so this case passes "
            "*because* the metric correctly flagged the mismatch."
        ),
        quiz=QuizAnswers(
            gender=Gender.UNISEX,
            budget_max=300.0,
            occasions=["sport"],
            style_selections=["sporty"],
        ),
        expected_dominant=Archetype.FORMAL,
        min_outfits=1,
        negative_check=True,
    ),
]
