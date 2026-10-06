# QUANTAREON TELEPAT

TELEPAT is a focused live AI astropsychologist assembled from four existing
QUANTAREON codebases:

- **quantareon-site** — production TELEPAT page, presentation layer and greeting media
- **quantareon-engine** — current deterministic Astrofractal calculations
- **QUANTARION Platform** — orchestration, voice/session patterns and memory integration
- **Dream Oracle** — selected Astrofractal bridge, interpretation and provider fallback ideas

## Product boundary

TELEPAT contains only:

1. live avatar
2. voice input/output
3. Astrofractal context
4. psychological/empathic conversation layers
5. user memory
6. replaceable conversational AI
7. orchestration
8. Modal CPU/GPU runtime

Payments, store logic, Telegram bots, dream interpretation, runes and unrelated
legacy modules stay outside this repository.

## Runtime pipeline

```
Browser microphone
  -> Deepgram Nova-3 streaming STT
  -> Session Manager
  -> Orchestrator
      -> relevant MemoryAdapter context
      -> cached AstroSummary
      -> Psychology / Empathy / Integrator context
  -> Conversation LLM Router
      -> Groq / Gemini / OpenAI / Claude / mock fallback
  -> TTS Router
      -> Yandex SpeechKit / Ermil (RU)
      -> Microsoft Andrew Multilingual (fallback / other languages)
  -> GPU Avatar Worker
  -> live TELEPAT in browser
```

## Session bootstrap

The browser restores a TELEPAT `user_id` and creates a session while the
greeting video can already be playing.

When birth data is available:

```
identity + memory recall
        |
        +---- deterministic Astrofractal
                  |
                  v
             Gemini Astro
                  |
                  v
             AstroSummary
                  |
                  v
             session cache
```

AstroSummary is keyed by a fingerprint of the birth profile and reused instead
of recalculating on every message.

## Current state — version 0.5.0

The TELEPAT CPU backend is deployed and running on Modal.

Development endpoint:

`https://makx518--quantareon-telepat-web.modal.run`

Confirmed in the live Modal environment:

- `/health` responds successfully
- `/health/providers` exposes provider configuration only as booleans
- `/health/readiness` separates core readiness from external-provider readiness
- `/health/provider-contract` lists missing configuration names without values
- `/health/config-preflight` validates provider/runtime policy before network probes
- `/health/production-readiness` lists remaining product blockers
- `/health/metrics` exposes privacy-safe latency/error aggregates
- `/session/bootstrap` creates/reuses TELEPAT identity and session
- `/chat` completes an orchestrated turn
- `/ws/voice` accepts a real WebSocket connection
- deterministic Astrofractal runs inside Modal and produces the natal machine output
- browser/voice protocol returns a controlled STT status when Deepgram is absent
- HTTP, WebSocket and concurrency smoke tests run automatically after Modal deployment
- expensive chat/Astro/voice-connect paths are rate-limited
- Memory API supports configurable auth header/scheme without changing the adapter
- chat request idempotency makes bounded POST retries safe
- per-session turn and Astro preparation locks prevent duplicate LLM/Gemini work
- voice sessions enforce idle and maximum-duration cost guards

The deterministic core is ready. Real external providers are not yet attached
to the Modal environment, so current live conversation falls back to the mock
provider and voice reports Deepgram/TTS as unconfigured.

The named Modal Secret `quantareon-telepat-secrets` always exists and is
attached unconditionally to the CPU runtime. GitHub provider-sync automation
merge-updates non-empty credentials/runtime policy into it and then chains:
`Provider Sync -> Modal Deploy -> Provider Smoke`.

When real provider credentials are present, the same diagnostics begin testing:

- Gemini Astro
- conversation LLM provider(s)
- Deepgram
- Yandex Ermil / Microsoft Andrew
- Memory API

No architecture change is required.

## Voice

Implemented:

- PCM16 mono 16 kHz browser transport
- Deepgram Nova-3 interim/final transcript handling
- multilingual language routing
- VAD-driven barge-in
- browser-playback-aware interruption
- Yandex Ermil -> Andrew fallback
- browser MP3 playback protocol
- per-utterance automatic language selection
- clean upstream-STT disconnect handling
- bounded idle/max session lifetime and browser `session_end` handling

The next voice gate is a real provider-backed run:
`microphone -> Deepgram -> LLM -> TTS -> browser`.

## Production hardening already in place

- bounded session TTL/history/session-count
- one active Modal CPU container while session state is in-process
- atomic conversation history commit only after successful LLM response
- explicit 503 / voice `stage=llm` for real provider outages
- graceful drain of background Memory writes
- privacy-safe in-process latency metrics
- provider configuration contract and production readiness report
- fixed-window rate limits for expensive public routes
- engine-neutral avatar benchmark harness
- stable SessionStore boundary for future shared session persistence
- runtime configuration preflight
- bounded LRU chat idempotency cache
- normalized cached-read/cache-write/thinking token accounting

## Modal CPU / GPU split

TELEPAT uses two independent Modal Apps:

- `quantareon-telepat` — CPU FastAPI/orchestration/providers
- `quantareon-telepat-avatar` — optional L4 avatar worker

The CPU app always deploys without requiring GPU billing. GPU deployment is
opt-in through `TELEPAT_AVATAR_GPU_ENABLED=1` and never changes the CPU Modal
object graph.

For the current in-process SessionStore, the CPU web function is temporarily
limited to one container. The stable `SessionStore` boundary allows a future
shared store to replace it without rewriting API/orchestration callers.

The avatar benchmark harness and deployed GPU preflight already measure/check
GPU identity, VRAM, benchmark assets, warm-up, p50/p95 render latency,
real-time factor and output size before an engine is selected.

## Automation

Normal development does not require a local Modal CLI.

GitHub Actions provides:

- **TELEPAT CI** — compile + pytest
- **TELEPAT Modal Provider Sync** — merge-safe Modal Secret/runtime config sync
- **TELEPAT Modal Deploy** — CPU deploy + live HTTP/WebSocket/concurrency smoke
- **TELEPAT Modal Smoke** — deployed provider probe and optional GPU preflight

See [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md),
[VOICE_PROTOCOL.md](VOICE_PROTOCOL.md) and [MODAL_SETUP.md](MODAL_SETUP.md).
