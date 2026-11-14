#!/usr/bin/env python3
"""Forecast Polymarket Yes prices, 240 minutes ahead, 5 quantiles.

Approach (adaptive multi-window volatility, mean-reverting spread):
  * The median forecast is the checkpoint price: over a 4-hour window these
    probability prices show no exploitable drift (every drift variant tested
    on the practice cases made the pinball loss worse), so drift is 0.
  * The spread is driven by the market's own recent 1-minute moves.  For
    each market we measure the root-mean-square of the 1-minute price
    changes over three trailing windows and blend them:
        sigma = 0.50 * rms(60 min) + 0.25 * rms(30 min) + 0.25 * rms(360 min)
    The short windows react to the current regime (a burst of ticks widens
    the forecast at once); the 6-hour window keeps a memory of the slower
    regime so a market that has been jumpy stays wider than a dead one.
    sigma is floored at 0.0006 (a market that has not moved at all lately
    can still move) and capped at 0.01 (one freak jump in the window must
    not blow the whole forecast up).
  * The spread grows sub-diffusively, like h ** 0.35 instead of sqrt(h):
    these prices are step-like and mean-reverting, so the realised
    dispersion over 4 hours grows much slower than a random walk's.  The
    exponent 0.35 was tuned on the practice cases (0.5 scores clearly
    worse, 0.25 worse again).
  * Quantile offsets use z = [-1.75, -0.67449, 0, 0.67449, 1.75]: slightly
    fatter outer tails than the normal 1.645, because the moves are
    jump-driven and the 5%/95% quantiles need to reach the occasional
    jump; the inner quantiles stay at the normal values.
  * Every row is clamped to [0, 1], rounded to 6 decimals and sorted so
    the quantiles are non-decreasing.

Short-history fallback (the final FAA markets were created on 2026-11-13,
so a case may hold only a handful of prices): with fewer than two prices
there are no diffs and sigma falls back to the floor 0.0006 with drift 0,
i.e. the house baseline's shape at a much smaller scale; with a few
prices the RMS windows simply use however many diffs exist.

Pure Python 3.13 standard library, no network, deterministic: the same
case always produces the same bytes.  Reads every *.in file in
$MAKEFUN_INPUT_DIR (default /input) and writes one /output/<id>.out per
case to $MAKEFUN_OUTPUT_DIR (default /output).
"""

import json
import math
import os
import sys

# Quantile offsets: level -> z.  Outer levels widened to 1.75 for the
# jump-driven tails; inner levels at the standard normal values.
Z_BY_TAU = {0.05: -1.75, 0.25: -0.6744897501960817, 0.5: 0.0,
            0.75: 0.6744897501960817, 0.95: 1.75}

SIGMA_FLOOR = 0.0006
SIGMA_CAP = 0.01
SPREAD_EXPONENT = 0.35
# (weight, window in minutes) for the RMS of 1-minute changes.
VOL_WINDOWS = ((0.50, 60), (0.25, 30), (0.25, 360))


def _rms(diffs, window):
    """Root-mean-square of the last `window` diffs (or all, if fewer)."""
    tail = diffs[-window:] if window < len(diffs) else diffs
    if not tail:
        return 0.0
    return math.sqrt(sum(d * d for d in tail) / len(tail))


def forecast_market(prices, quantiles, horizon=240):
    """One market's forecast over `horizon` rows.  `prices` is the
    1-minute grid."""
    if prices:
        x = float(prices[-1])
    else:  # no history at all: centre on 0.5 with the floor spread
        x = 0.5
    diffs = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
    sigma = sum(w * _rms(diffs, win) for w, win in VOL_WINDOWS)
    if sigma < SIGMA_FLOOR:
        sigma = SIGMA_FLOOR
    elif sigma > SIGMA_CAP:
        sigma = SIGMA_CAP
    zetas = [Z_BY_TAU.get(float(t), 0.0) for t in quantiles]
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * (h ** SPREAD_EXPONENT)
        row = []
        for z in zetas:
            v = x + z * spread
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            row.append(round(v, 6))
        row.sort()
        rows.append(row)
    return rows


def forecast_case(case):
    quantiles = case.get("quantiles") or [0.05, 0.25, 0.5, 0.75, 0.95]
    horizon = int(case.get("horizon_minutes") or 240)
    forecasts = []
    for market in case["markets"]:
        forecasts.append({
            "id": market["id"],
            "q": forecast_market(market.get("prices") or [], quantiles,
                                 horizon),
        })
    return {"forecasts": forecasts}


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(output_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(input_dir) if n.endswith(".in"))
    if not names:
        print("no .in files in %s" % input_dir, file=sys.stderr)
        return 1
    for name in names:
        case_id = name[:-3]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        out = forecast_case(case)
        text = json.dumps(out, separators=(",", ":"), sort_keys=False)
        with open(os.path.join(output_dir, case_id + ".out"),
                  "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
