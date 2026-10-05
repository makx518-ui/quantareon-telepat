# QUANTAREON TELEPAT

TELEPAT is a focused live AI astropsychologist assembled from four existing
QUANTAREON codebases:

- **quantareon-site** — production page, presentation layer and greeting media
- **quantareon-engine** — current Astrofractal calculations
- **QUANTARION Platform** — orchestration, voice/session patterns and memory integration
- **Dream Oracle** — selected Astrofractal bridge/prompt/fallback ideas

## Product boundary

TELEPAT is intentionally narrow. It contains:

1. live avatar
2. voice input/output
3. Astrofractal context
4. psychological/empathic conversation layers
5. memory
6. replaceable conversational AI
7. orchestration
8. Modal CPU/GPU runtime

Payments, store logic, Telegram bots, dream interpretation, runes and unrelated
legacy modules stay outside this repository.

## Runtime pipeline

```
Browser microphone
  -> Deepgram streaming STT
  -> Session Manager
  -> Orchestrator
      -> relevant Memory
      -> cached AstroSummary
      -> Psychology / Empathy Context
  -> Conversation LLM Router
  -> TTS Router
      -> Yandex SpeechKit / Ermil (RU)
      -> Microsoft Andrew Multilingual (fallback / other languages)
  -> GPU Avatar Worker
  -> live TELEPAT in browser
```

## Session bootstrap

The browser restores a TELEPAT `user_id` and creates a session while the
greeting video can already be playing.

If birth data is available, bootstrap can prepare Astrofractal context in the
same phase:

```
identity + memory recall
        |
        +---- Astrofractal calculation
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

AstroSummary is keyed by a fingerprint of the birth profile and is reused
instead of recalculating on every message.

## Current state — 5 October 2026

Implemented and covered by CI:

- FastAPI health/chat/session/voice endpoints
- Session Manager and Orchestrator
- replaceable LLM Router with fallbacks
- deterministic Astrofractal donor engine
- Gemini Astro structured-output contract
- session-level AstroSummary cache
- remote Memory adapter and compact memory context
- psychology/empathy/integrator context layers
- Deepgram streaming STT with interim/final transcripts
- barge-in cancellation
- Yandex Ermil Russian TTS
- Microsoft Andrew multilingual fallback
- browser session/voice/avatar controllers
- Modal CPU runtime and L4 GPU boundary
- private Modal provider smoke runner

The next runtime gate is:

    modal run deploy/smoke.py

That command exercises real provider credentials inside Modal without exposing
secret values. After the provider smoke passes, the remaining work is the
browser microphone end-to-end test, avatar-engine benchmark on L4, and final
integration into `quantareon-site`.

See [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md),
[VOICE_PROTOCOL.md](VOICE_PROTOCOL.md) and [MODAL_SETUP.md](MODAL_SETUP.md).
