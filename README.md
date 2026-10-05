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

## Current state — version 0.4.0

The TELEPAT CPU backend is deployed and running on Modal.

Development endpoint:

`https://makx518--quantareon-telepat-web.modal.run`

Confirmed in the live Modal environment:

- `/health` responds successfully
- `/health/providers` exposes provider configuration only as booleans
- `/health/readiness` separates core readiness from external-provider readiness
- `/session/bootstrap` creates/reuses TELEPAT identity and session
- `/chat` completes an orchestrated turn
- `/ws/voice` accepts a real WebSocket connection
- deterministic Astrofractal runs inside Modal and produces the natal machine output
- browser/voice protocol returns a controlled STT status when Deepgram is absent
- HTTP and WebSocket smoke tests run automatically after Modal deployment

The deterministic core is ready. Real external providers are not yet attached
to the Modal environment, so current live conversation falls back to the mock
provider and voice reports Deepgram/TTS as unconfigured.

When the named Modal Secret `quantareon-telepat-secrets` becomes available,
the GitHub workflows automatically attach it and begin testing real:

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

The next voice gate is a real provider-backed run:
`microphone -> Deepgram -> LLM -> TTS -> browser`.

## Modal CPU / GPU split

CPU deployment is independent from GPU registration.

The API can run without GPU billing. L4 registration is opt-in through
`TELEPAT_REGISTER_GPU=1`; the actual lip-sync engine remains intentionally
unselected until benchmark time.

For the current in-memory Session Manager, the CPU web function is temporarily
limited to one container. This constraint can be removed after shared session
state is attached.

## Automation

Normal development does not require a local Modal CLI.

GitHub Actions provides:

- **TELEPAT CI** — compile + pytest
- **TELEPAT Modal Smoke** — deterministic core and real provider checks when configured
- **TELEPAT Modal Deploy** — deploy + live HTTP + live WebSocket smoke

See [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md),
[VOICE_PROTOCOL.md](VOICE_PROTOCOL.md) and [MODAL_SETUP.md](MODAL_SETUP.md).
