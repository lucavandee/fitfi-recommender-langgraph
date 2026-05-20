# fitfi-recommender-langgraph

A Python LangGraph port of the recommendation pipeline from [FitFi](https://github.com/lucavandee/FitFi), a TypeScript fashion-recommendation app.

This is an exercise port. Production FitFi runs its pipeline client-side in TypeScript; this repository ports each pipeline stage to a LangGraph node so the framework patterns (typed state, sequential nodes, conditional edges) are exercised against a familiar problem domain.

Not a replacement for the production engine.

## What the graph does

```
START → archetype → filter → reclassify → [photo_enhance?] → assemble → rank → diversity → END
```

| Node | Responsibility |
|---|---|
| `archetype` | Map quiz answers to dominant + secondary archetype with mix factor |
| `filter` | Drop products that fail budget, gender, or stock filters |
| `reclassify` | Group filtered products by outfit slot (top, bottom, shoes, dress) |
| `photo_enhance` | Conditional. Boost archetype weights of color-compatible items if a color profile is in state |
| `assemble` | Combine top-N products per slot into outfit candidates |
| `rank` | Score each outfit by archetype match, weighted by the mix factor |
| `diversity` | Drop outfits sharing the same brand signature; keep top 5 |

The `photo_enhance` node only runs when a `color_profile` is present in the input state. This demonstrates LangGraph conditional edges.

## Running

Requirements: Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run python main.py        # four sample queries through the graph
uv run python -m evals       # the eval suite
```

The demo invokes the graph four times: a formal-male scenario without and with an autumn color profile (showing the conditional edge), a sporty-unisex scenario, and a vintage-unisex scenario.

## Eval suite

The `evals/` package runs a small set of hand-crafted cases through the graph and scores the output against expectations. Each case states an input quiz plus an expected dominant archetype, a minimum outfit count, and (optionally) a per-item price cap.

Metrics per case:

| Metric | What it checks |
|---|---|
| `archetype_dominant_ok` | Graph derived the expected dominant archetype |
| `archetype_secondary_ok` | (If specified) graph derived the expected secondary archetype |
| `min_outfits_ok` | At least N outfits were returned |
| `gender_compliance` | Every returned item matches the quiz gender or is unisex |
| `budget_compliance` | Every returned item is within `quiz.budget_max` |
| `item_price_cap_ok` | (If specified) every returned item is within a tighter per-item cap |
| `stock_compliance` | Every returned item is `in_stock` |
| `brand_diversity_ok` | No two returned outfits share the same brand signature |

A case passes when all applicable metrics are `True`. The runner exits non-zero on any failure, so it can drop into CI later.

### Negative-check cases

An `EvalCase` can set `negative_check=True`. The runner then inverts the pass condition: the case passes only if at least one metric *fails*. This proves the suite actually detects wrong expectations rather than rubber-stamping every run. One such case is included as a sanity check.

Current state: 7/7 cases pass (3 archetype scenarios, the photo-enhance conditional, a budget-constrained edge case, an empty-quiz default, and one negative-check case demonstrating mismatch detection).

To add a case, append an `EvalCase` to `evals/cases.py`. To add a metric, extend `_score_case` in `evals/runner.py`.

## Project layout

```
fitfi_rec/
  types.py     Pydantic models (Product, QuizAnswers, Outfit, ...)
  state.py     TypedDict for LangGraph state
  nodes.py     Node functions, one per pipeline stage
  graph.py     Wires nodes into a compiled StateGraph
  seed.py      Synthetic product catalog and sample quizzes
evals/
  cases.py     Hand-crafted EvalCase definitions
  runner.py    Metrics + report
  __main__.py  CLI entry (`python -m evals`)
main.py        Demo entry point
```

## Status

Working v1. The graph compiles and runs end-to-end on synthetic data. The eval suite passes all six cases. Wider seed catalog, negative cases, and performance benchmarks are scoped for follow-up.

## Why this exists

To practice the LangGraph API against real recommendation logic, and to have a small public artifact that shows the same problem domain expressed as a graph rather than as the TypeScript modular pipeline that runs in production FitFi.

The architecture write-up for the original TypeScript engine: [FitFi/docs/ARCHITECTURE.md](https://github.com/lucavandee/FitFi/blob/main/docs/ARCHITECTURE.md).
