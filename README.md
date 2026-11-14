# Forecast Polymarket FAA outage attribution prices — zech entry

Entry for make.fun competition `polymarket-faa-attribution-02` (account
@vivid-pika-25, wallet `74pauFpEwsRxyX5oSrcv9qHuUtckra8Ny5APDwdRgkKZ`).

`main.py` (Python 3.13, standard library only, no network) forecasts the
Yes price of every market in a case, 240 minutes ahead, at the quantiles
0.05 / 0.25 / 0.5 / 0.75 / 0.95. It reads every `*.in` file in
`$MAKEFUN_INPUT_DIR` (default `/input`) and writes one `/output/<id>.out`
per case to `$MAKEFUN_OUTPUT_DIR` (default `/output`).

## Method

- **Median = checkpoint price.** Over a 4-hour window these probability
  prices show no exploitable drift: every drift variant tested on the
  practice cases made the pinball loss worse, so drift is 0.
- **Adaptive volatility.** Sigma is the RMS of the 1-minute price changes
  blended over three trailing windows — 50% last 60 min, 25% last 30 min,
  25% last 6 hours — floored at 0.0006 and capped at 0.01. Short windows
  react to the current regime; the 6-hour window remembers the slower
  regime.
- **Mean-reverting spread.** The spread grows like `h ** 0.35`, not
  `sqrt(h)`: these prices are step-like and mean-reverting, so realised
  dispersion over 4 hours grows much slower than a random walk's.
- **Fatter outer tails.** Quantile offsets `z = [-1.75, -0.67449, 0,
  0.67449, 1.75]` — the 5%/95% quantiles reach the occasional jump.
- **Short-history fallback.** The final FAA markets were created on
  2026-11-13, so a case may hold only a handful of prices. With fewer
  diffs the RMS windows use whatever exists; with none, sigma falls back
  to the floor with drift 0.

## Local validation (practice cases p00–p05, NVIDIA event)

Actual prices after each checkpoint were fetched from Polymarket's public
price history (`clob.polymarket.com/prices-history`) and scored with the
competition's pinball loss:

| model | practice loss | median error | 90% coverage |
|---|---|---|---|
| house baseline | 0.363589 | 0.767503 | 0.949642 |
| this entry | **0.266187** | 0.767503 | 0.892741 |

26.8% below the house baseline on the practice set. (Per the rules, the
practice score is no guide to the final — the final markets are different
and much younger — but the method is regime-adaptive rather than tuned to
one event.)

Two runs on the same input produce byte-identical output; all six practice
cases run in ~0.3 s total, far inside the 8 s per-case limit.

## Run locally

```sh
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see LICENSE.
