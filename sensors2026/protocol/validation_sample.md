# Blind validation subsample - draw record

Written by `scripts/32_validation_sample.py`. Each stratum is drawn once.
The draw is `random.Random(f"{SEED}-{stratum}").sample(sorted(eligible), n)`.

## Stratum `baseline` - drawn 2026-09-26

- Seed: `20260926-baseline`
- Frame: 88 records; eligible 83; drawn 24
- Excluded before the draw:
  - `paper031` - calibration: model output already seen
  - `paper033` - calibration: model output already seen
  - `paper041` - calibration: model output already seen
  - `paper043` - calibration: model output already seen
  - `paper056` - calibration: model output already seen
- Drawn: `paper003`, `paper009`, `paper010`, `paper011`, `paper012`, `paper013`, `paper018`, `paper027`, `paper036`, `paper037`, `paper039`, `paper042`, `paper044`, `paper045`, `paper047`, `paper055`, `paper057`, `paper065`, `paper066`, `paper069`, `paper075`, `paper080`, `paper081`, `paper083`

## Amendment A5 - 8 October 2026

Baseline stratum truncated to the first 18 drawn studies in record-id order,
decided before any agreement figure was computed (see `osf_protocol.md` A5).
Coded: `paper003` ... `paper065` (18). Not coded: `paper066`, `paper069`,
`paper075`, `paper080`, `paper081`, `paper083`.

## Stratum `round2` - drawn 2026-10-19

- Seed: `20260926-round2`
- Frame: 19 records; eligible 19; drawn 6
- Excluded before the draw:
- Drawn: `r2-0387`, `r2-0477`, `r2-0581`, `r2-0677`, `r2-0934`, `r2-1239`

## Round-2 stratum after full-text eligibility review - 20 October 2026

`r2-0581` was drawn on 19 October but P.Z. excluded it at full text on
20 October (low-level control only; see `fulltext_decisions.xlsx`) before
coding it. It is removed from the subsample and not replaced: the remaining
five round-2 studies were already coded, and a replacement would have been
drawn after round-2 extraction output existed. The validation subsample is
therefore 23 studies (18 baseline + 5 round 2), one fewer than amendment A5
states; this is reported as such.

