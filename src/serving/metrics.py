"""
metrics.py
Prometheus metric definitions for the classifier service.

These metrics are exposed at /metrics by prometheus-fastapi-instrumentator.
Standard HTTP metrics (request count, latency, in-progress) are added by the
instrumentator itself; this module defines the ML-specific custom metrics.

Metric design ties to the curator workflow:
  - top1_confidence captures how sure the model is about its #1 pick
  - confidence_gap (top1 − top2) captures the "needs human review" signal
    that drives the top-2 curator workflow
  - prediction_class_total catches class-distribution drift over time
  - input_text_length catches upstream pipeline failures (empty text_clean)
  - low_confidence_predictions_total is an explicit threshold-crossing counter
  - model_info is an info-style gauge labelled with the active run_id so
    Grafana queries can correlate metric values with the model version
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


# Below this top-1 probability, a prediction counts as "low confidence" and
# the curator should look. Threshold is conservative — at this floor the
# model is barely above random for a 6-class problem (1/6 ≈ 0.17).
LOW_CONFIDENCE_THRESHOLD = 0.5


top1_confidence = Histogram(
    "am2_top1_confidence",
    "Top-1 softmax probability per prediction. Distribution shifts here are an early drift signal.",
    buckets=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)

confidence_gap = Histogram(
    "am2_confidence_gap",
    "Top1 − top2 probability gap. Small gap = curator should compare the two candidates.",
    buckets=(0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0),
)

input_text_length = Histogram(
    "am2_input_text_length_chars",
    "Character length of text_clean as received. Spikes near zero indicate upstream scraping/cleaning failure.",
    buckets=(0, 50, 100, 200, 400, 800, 1600, 3200),
)

prediction_class_total = Counter(
    "am2_prediction_class_total",
    "Cumulative count of predictions per top-1 class. Watch for distribution drift over weeks.",
    ["class_name"],
)

low_confidence_predictions_total = Counter(
    "am2_low_confidence_predictions_total",
    f"Predictions where top-1 probability < {LOW_CONFIDENCE_THRESHOLD}. Rising rate signals data drift.",
)

model_info = Gauge(
    "am2_model_info",
    "Active model metadata. Always 1; the labels carry the information for correlation queries.",
    ["run_id", "variant"],
)
