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
