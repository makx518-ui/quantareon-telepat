# Avatar GPU Boundary

TELEPAT deliberately separates the avatar engine from the conversation stack.

## Fixed now

- Modal App: `quantareon-telepat`
- initial GPU class: L4
- GPU scales down after 60 seconds idle
- persistent Modal Volume: `quantareon-telepat-assets`
- mount: `/telepat-assets`
- conversation and voice code do not import any specific lip-sync model

Modal supports GPU-backed `@app.cls` containers with lifecycle/resource
options and persistent Volumes. The worker therefore scales independently from
the CPU FastAPI service.

## Not fixed yet

The actual lip-sync engine.

Candidates will be benchmarked using the final TELEPAT portrait/idle material
and the Ermil audio. Selection criteria:

1. identity stability
2. lip-sync accuracy
3. latency / real-time factor
4. L4 memory usage
5. ability to work from our base video/state library
6. license/commercial suitability
7. cold-start/model-load cost

Do not wire the browser directly to a model-specific API. The selected engine
must implement the common AvatarAdapter contract.


## Benchmark harness

Every candidate engine must implement `AvatarAdapter` and expose a stable
`name`. TELEPAT benchmarks candidates through
`telepat.avatar.benchmark.benchmark_avatar_adapter()`.

The automated technical comparison records:

- warm-up latency
- p50 render latency
- p95 render latency
- max render latency
- p50 real-time factor (`render_ms / audio_duration_ms`)
- average output size
- peak VRAM when the GPU adapter supplies a reader

The same final TELEPAT portrait/video source and the same Ermil audio sample
must be used for every candidate.

Human review remains separate and scores:

- identity stability
- lip-sync accuracy
- facial naturalness
- temporal artifacts
- gesture/state compatibility
- commercial/license suitability

Do not select an engine solely from speed. The winning adapter must satisfy both
the technical benchmark and the visual review.
