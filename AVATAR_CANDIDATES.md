# TELEPAT Avatar Engine Shortlist

This document fixes the candidate set for the first real Modal L4 benchmark.
It does **not** select the final engine in advance.

## Benchmark order

1. **MuseTalk 1.5 first** — interactive/realtime candidate.
2. **LatentSync second** — quality reference after MuseTalk metrics are captured.

MuseTalk is pinned for the first benchmark to upstream commit
`0a89dec45a0192b824e3cf4daf96c239440c5ed8`. The benchmark app remains
separate from the production GPU app until the candidate is validated.

## Candidate A — MuseTalk

Why it stays in the benchmark:

- official code license: MIT
- official project states that the trained model can be used for academic and
  commercial purposes, subject to dependency licenses
- audio-driven talking-face architecture fits TELEPAT's fixed-character design
- published implementation targets real-time generation, making it relevant
  for an interactive voice assistant rather than offline-only video generation

Known risks to measure:

- identity stability across longer responses
- temporal jitter around the mouth/face boundary
- quality when driven from TELEPAT's final portrait/state video material
- actual L4 throughput rather than published V100/A100-class results
- cold-start/model-load cost

## Candidate B — LatentSync

Why it stays in the benchmark:

- official repository license: Apache-2.0
- quality-focused lip-sync architecture
- suitable as the higher-quality reference even if its latency is worse
- useful comparison against MuseTalk for the quality/latency trade-off

Known risks to measure:

- L4 VRAM requirement
- cold-start time
- render latency / real-time factor
- integration complexity
- temporal identity consistency on TELEPAT's fixed character

## Excluded from the open-source commercial shortlist — Wav2Lip

The official open-source Wav2Lip repository/model is restricted to research,
academic and personal/non-commercial use.

Therefore TELEPAT must **not** ship the public Wav2Lip implementation in the
commercial product unless a separate commercial license is obtained.

It may remain only as a conceptual/reference baseline, not as a deployable
candidate in the default TELEPAT benchmark.

## Benchmark input must be identical

Every candidate receives the same:

1. final TELEPAT source portrait/video
2. Ermil audio sample
3. audio duration
4. speaking state
5. Modal L4 class
6. warm-up count and measured run count

No candidate-specific input optimization is allowed until the first comparison
is complete.

## Automated technical metrics

The common harness in `telepat/avatar/benchmark.py` records:

- warm-up latency
- p50 render latency
- p95 render latency
- maximum render latency
- p50 real-time factor
- average output bytes
- peak VRAM when available

## Human visual score

Technical speed alone does not choose the winner.

Each candidate is scored 1–5 for:

| Criterion | Weight |
| --- | ---: |
| TELEPAT identity stability | 30% |
| Lip-sync accuracy | 25% |
| Facial naturalness | 15% |
| Temporal stability / jitter | 10% |
| Latency / real-time factor | 10% |
| Integration reliability | 5% |
| Commercial/license suitability | 5% |

## Selection rule

A candidate is rejected immediately if:

- its license is incompatible with TELEPAT commercial use;
- it cannot keep the TELEPAT identity stable;
- it cannot run reliably on the chosen Modal GPU class.

Among the remaining candidates, select the highest weighted visual/technical
score. Do not hard-code the engine into the browser; the winner must remain
behind `AvatarAdapter`.
