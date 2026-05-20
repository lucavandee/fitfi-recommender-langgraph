"""Eval runner: invoke the graph on each case and score against expectations.

Metrics computed per case:
    archetype_dominant_ok    Expected dominant archetype was derived.
    archetype_secondary_ok   Expected secondary archetype was derived (if specified).
    min_outfits_ok           Returned at least `min_outfits` final outfits.
    gender_compliance        Every returned item matches quiz.gender or is unisex.
    budget_compliance        Every returned item is at or below quiz.budget_max.
    item_price_cap_ok        If max_item_price is set, every item is at or below it.
    stock_compliance         Every returned item has in_stock=True.
    brand_diversity_ok       No duplicate brand signatures across returned outfits.

A case passes when all applicable metrics are True.
"""

from typing import Any
from pydantic import BaseModel, Field

from fitfi_rec.graph import build_graph
from fitfi_rec.types import Gender, RankedOutfit
from fitfi_rec.seed import CATALOG
from .cases import CASES, EvalCase


class CaseResult(BaseModel):
    case_name: str
    passed: bool
    metrics: dict[str, bool]
    failures: list[str] = Field(default_factory=list)
    outfit_count: int = 0
    is_negative: bool = False


class EvalReport(BaseModel):
    results: list[CaseResult]

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.pass_count / self.total if self.total else 0.0


def _score_case(case: EvalCase, result: dict[str, Any]) -> CaseResult:
    metrics: dict[str, bool] = {}
    failures: list[str] = []

    archetype = result.get("archetype")
    if archetype is None:
        metrics["archetype_dominant_ok"] = False
        failures.append("graph returned no archetype")
    else:
        ok_dom = archetype.dominant == case.expected_dominant
        metrics["archetype_dominant_ok"] = ok_dom
        if not ok_dom:
            failures.append(
                f"dominant: expected {case.expected_dominant.value}, "
                f"got {archetype.dominant.value}"
            )
        if case.expected_secondary is not None:
            ok_sec = archetype.secondary == case.expected_secondary
            metrics["archetype_secondary_ok"] = ok_sec
            if not ok_sec:
                failures.append(
                    f"secondary: expected {case.expected_secondary.value}, "
                    f"got {archetype.secondary.value}"
                )

    final: list[RankedOutfit] = result.get("final", [])
    ok_min = len(final) >= case.min_outfits
    metrics["min_outfits_ok"] = ok_min
    if not ok_min:
        failures.append(f"min_outfits: expected ≥{case.min_outfits}, got {len(final)}")

    if final:
        # Compliance metrics over every item in every outfit.
        all_items = [p for r in final for p in r.outfit.items.values()]

        ok_gender = all(
            p.gender == case.quiz.gender or p.gender == Gender.UNISEX for p in all_items
        )
        metrics["gender_compliance"] = ok_gender
        if not ok_gender:
            bad = next(
                p
                for p in all_items
                if not (p.gender == case.quiz.gender or p.gender == Gender.UNISEX)
            )
            failures.append(f"gender violation: {bad.brand} {bad.name} ({bad.gender.value})")

        ok_budget = all(p.price <= case.quiz.budget_max for p in all_items)
        metrics["budget_compliance"] = ok_budget
        if not ok_budget:
            bad = next(p for p in all_items if p.price > case.quiz.budget_max)
            failures.append(
                f"budget violation: {bad.brand} {bad.name} €{bad.price:.0f} "
                f"> €{case.quiz.budget_max:.0f}"
            )

        ok_stock = all(p.in_stock for p in all_items)
        metrics["stock_compliance"] = ok_stock
        if not ok_stock:
            failures.append("an out-of-stock item was returned")

        if case.max_item_price is not None:
            ok_cap = all(p.price <= case.max_item_price for p in all_items)
            metrics["item_price_cap_ok"] = ok_cap
            if not ok_cap:
                bad = next(p for p in all_items if p.price > case.max_item_price)
                failures.append(
                    f"item price cap: {bad.brand} {bad.name} €{bad.price:.0f} "
                    f"> €{case.max_item_price:.0f}"
                )

        # Brand-signature diversity check: ensure the diversity node did its job.
        signatures = [tuple(sorted(p.brand for p in r.outfit.items.values())) for r in final]
        ok_div = len(set(signatures)) == len(signatures)
        metrics["brand_diversity_ok"] = ok_div
        if not ok_div:
            failures.append("duplicate brand signature in final outfits")

    metrics_all_ok = all(metrics.values())
    # A negative-check case passes when at least one metric fails: that proves
    # the suite actually catches the issue rather than rubber-stamping.
    passed = (not metrics_all_ok) if case.negative_check else metrics_all_ok
    return CaseResult(
        case_name=case.name,
        passed=passed,
        metrics=metrics,
        failures=failures,
        outfit_count=len(final),
        is_negative=case.negative_check,
    )


def run(cases: list[EvalCase] = CASES) -> EvalReport:
    app = build_graph()
    results: list[CaseResult] = []
    for case in cases:
        initial: dict[str, Any] = {"quiz": case.quiz, "products": CATALOG}
        if case.color_profile is not None:
            initial["color_profile"] = case.color_profile
        graph_result = app.invoke(initial)
        results.append(_score_case(case, graph_result))
    return EvalReport(results=results)


def print_report(report: EvalReport) -> None:
    print()
    print(f"FitFi LangGraph eval suite  ·  {report.pass_count}/{report.total} passed "
          f"({report.pass_rate * 100:.0f}%)")
    print("-" * 76)
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        tag = " (negative)" if r.is_negative else ""
        print(f"[{status}]{tag} {r.case_name}  ({r.outfit_count} outfits)")
        for metric, value in r.metrics.items():
            mark = "ok" if value else "fail"
            print(f"        - {metric}: {mark}")
        for f in r.failures:
            note = " (expected, negative-check)" if r.is_negative else ""
            print(f"        ! {f}{note}")
    print()
