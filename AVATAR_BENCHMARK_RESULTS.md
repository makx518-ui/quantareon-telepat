# TELEPAT Avatar L4 Benchmark Results

Date: 2026-10-06

Hardware: NVIDIA L4, 23,034 MiB VRAM reported by `nvidia-smi`.

## Input

Both candidates were measured with the same Modal L4 class, the same seeded
benchmark video and the same Yandex Ermil MP3.

Current technical benchmark source:

- `/telepat-assets/benchmark/source.mp4`
- public MuseTalk demo source, benchmark-only
- not the final TELEPAT identity

Audio:

- `/telepat-assets/benchmark/ermil-benchmark.mp3`
- duration: about 6.216 seconds

Each technical benchmark used one warm-up render and three measured renders.

## Results

| Metric | MuseTalk 1.5 | LatentSync 1.6 |
| --- | ---: | ---: |
| Warm-up | 251.42 s | 260.77 s |
| p50 render | 20.81 s | 200.81 s |
| p95 render | 20.95 s | 201.08 s |
| Max render | 20.95 s | 201.08 s |
| p50 real-time factor | 3.3486× | 32.3052× |
| Peak VRAM | 5.49 GiB | 20.60 GiB |
| Average output | 658,842 B | 1,162,185 B |

## Technical interpretation

MuseTalk is approximately 9.65× faster than LatentSync on the identical L4
benchmark and uses approximately 3.75× less peak VRAM.

Neither current full-MP4 path is yet real-time because both real-time factors
are above 1.0. MuseTalk is nevertheless the only candidate close enough to the
interactive requirement to justify optimization.

LatentSync 1.6 is retained as the quality reference. At roughly 201 seconds to
render about 6.2 seconds of speech, it is not suitable as the default
turn-by-turn live TELEPAT renderer on an L4 without a radically different
inference strategy.

## Important latency caveat

The current MuseTalk adapter measures end-to-end MP4 generation. It includes
audio feature extraction, frame compositing, writing individual frames and
FFmpeg packaging. The upstream real-time architecture precomputes avatar
materials and is designed to avoid part of this per-turn overhead.

Therefore the next MuseTalk engineering target is not a different model. It is
to replace the full-file render boundary with a preprocessed, chunked/streaming
delivery path and benchmark time-to-first-frame plus sustained FPS.

## Selection state

Technical winner: **MuseTalk 1.5**.

Final production promotion remains pending visual review of identical rendered
samples for:

1. identity stability
2. lip-sync accuracy
3. facial naturalness
4. temporal artifacts

After visual review, the selected adapter is promoted behind the existing
`AvatarGPUWorker -> ModalAvatarAdapter -> AvatarService` boundary.
