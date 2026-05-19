"""Demo entry point for the FitFi recommender LangGraph port.

Run with:
    uv run python main.py
"""

from fitfi_rec.graph import build_graph
from fitfi_rec.seed import (
    CATALOG,
    QUIZ_FORMAL_MALE,
    QUIZ_SPORTY_UNISEX,
    QUIZ_VINTAGE_UNISEX,
    COLOR_PROFILE_AUTUMN,
)


def _print_result(label: str, result: dict) -> None:
    print(f"\n=== {label} ===")
    archetype = result.get("archetype")
    if archetype:
        print(
            f"Dominant: {archetype.dominant.value}  |  "
            f"Secondary: {archetype.secondary.value}  |  "
            f"Mix: {archetype.mix_factor:.2f}"
        )

    final = result.get("final", [])
    print(f"Top {len(final)} outfits:")
    for i, r in enumerate(final, start=1):
        names = " + ".join(f"{p.brand} {p.name}" for p in r.outfit.items.values())
        print(f"  {i}. score={r.score:.2f}  €{r.outfit.total_price:.0f}  {names}")


def main() -> None:
    app = build_graph()

    result1 = app.invoke({"quiz": QUIZ_FORMAL_MALE, "products": CATALOG})
    _print_result("Formal male, no color profile", result1)

    result2 = app.invoke({
        "quiz": QUIZ_FORMAL_MALE,
        "products": CATALOG,
        "color_profile": COLOR_PROFILE_AUTUMN,
    })
    _print_result("Formal male, autumn color palette (photo_enhance ON)", result2)

    result3 = app.invoke({"quiz": QUIZ_SPORTY_UNISEX, "products": CATALOG})
    _print_result("Sporty unisex", result3)

    result4 = app.invoke({"quiz": QUIZ_VINTAGE_UNISEX, "products": CATALOG})
    _print_result("Vintage unisex", result4)


if __name__ == "__main__":
    main()
