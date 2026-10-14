# Backtesting — Calibration

How the system measures whether a stated probability means what it says.

## The question

When the model says "70%", does the event happen ~70% of the time? That is
*calibration* — the agreement between predicted probability and observed
frequency — and it is what makes a probability auditable rather than a number
that merely sounds confident.

## The existing quant layer (reused)

`trading/quant/calibration.py` supplies the full machinery, reused verbatim:

- **`PlattScaler`** — fits a 1-D logistic map `sigmoid(a·score + b)` on a
  held-out slice so a raw model score becomes a calibrated probability.
- **`CalibrationReport.evaluate(p, y, bins)`** — the metric bundle:
  - `brier` — mean squared error between probability and outcome (lower better).
  - `log_loss` — binary cross-entropy.
  - `accuracy` — share of thresholded predictions matching the outcome.
  - `ece` — Expected Calibration Error: the bin-weighted gap between mean
    predicted probability and observed frequency (0 = perfectly calibrated).
  - `base_rate` — the empirical frequency (the baseline any real model must beat).
  - `reliability_bins` — per-bin `mean_predicted` vs `observed_frequency`, the
    raw material of a calibration/reliability curve.

## Where calibration plugs into the outcome record

The enriched outcome carries `probability_up` when the prediction stated a
calibrated estimate. `PredictionPerformanceService.summarize` (existing) runs
`CalibrationReport.evaluate` over every resolved outcome that carried a
reliable `predicted_p_up`, with `y = 1` if the realised move was up — the same
binary label the model was trained against.

## The honesty rule: never recalibrate on thin data

The spec is explicit — **do not change probabilities automatically based on
insufficient data**. The engine reports calibration metrics over whatever
resolved sample exists and flags `is_reliable = False` when the sample is thin
or mock; it never silently refits the calibrator on too little data. A
calibration read on a handful of outcomes is reported *as* a thin read, not as
a corrected probability curve.

## Reading the calibration curve

`reliability_bins` tells you per-bin whether the model is over- or
under-confident: a bin with `mean_predicted 0.8, observed_frequency 0.6` is
over-confident there; `mean_predicted 0.3, observed 0.5` under-confident. `ece`
summarises the gap in one number; `brier` and `log_loss` score the whole
probability output. None of these alone is a verdict — they are the audit
trail of whether the probabilities can be trusted.
