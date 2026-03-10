from __future__ import annotations

from app.models.enums import Layer
from app.models.responses import CheckResult, LayerResult, SignalScore

LAYER_CONFIG: dict[Layer, tuple[str, float]] = {
    Layer.SITE_FOUNDATION:    ("Site Foundation",    0.20),
    Layer.INDEXABILITY_SPEED:  ("Indexability & Speed", 0.10),
    Layer.GRAPH_DISCOVERY:    ("Graph & Discovery",  0.10),
    Layer.NODE_READABILITY:   ("Node Readability",   0.15),
    Layer.AUTHORITY_TRUST:    ("Authority & Trust",  0.15),
    Layer.LLM_EXTRACTION:     ("LLM Extraction",     0.15),
    Layer.CONTENT_QUALITY:    ("Content Quality",    0.15),
}


def grade_from_score(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 55:
        return "C-"
    if score >= 50:
        return "D"
    return "F"


def compute_signal_score(checks: list[CheckResult]) -> SignalScore:
    """Compute per-layer scores and weighted overall SIGNAL score."""
    # Group checks by layer
    by_layer: dict[Layer, list[CheckResult]] = {}
    for c in checks:
        by_layer.setdefault(c.layer, []).append(c)

    layers: list[LayerResult] = []
    overall = 0.0

    for layer in Layer:
        label, weight = LAYER_CONFIG[layer]
        layer_checks = by_layer.get(layer, [])

        # Filter out N/A checks
        scored = [c for c in layer_checks if c.status != "n/a"]
        if scored:
            layer_score = sum(c.score for c in scored) / len(scored)
        else:
            layer_score = 0.0

        overall += layer_score * weight

        layers.append(
            LayerResult(
                layer=layer,
                label=label,
                weight=weight,
                score=round(layer_score, 1),
                grade=grade_from_score(layer_score),
                checks=layer_checks,
            )
        )

    return SignalScore(
        overall_score=round(overall, 1),
        grade=grade_from_score(overall),
        layers=layers,
    )
