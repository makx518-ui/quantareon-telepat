# QUANTAREON TELEPAT

TELEPAT is a focused AI astropsychologist assembled from four existing QUANTAREON codebases:

- **quantareon-site** — user interface and TELEPAT presentation layer
- **quantareon-engine** — Astrofractal calculations and current astrology engine
- **QUANTARION Platform** — orchestration, voice pipeline, session logic and memory adapters
- **Dream Oracle** — Astrofractal bridge, interpretation prompts and useful fallbacks

## Product boundary

TELEPAT is intentionally narrow. It contains:

1. live avatar
2. voice input/output
3. Astrofractal context
4. psychological/empathic conversation layers
5. memory
6. conversational AI
7. orchestration
8. Modal CPU/GPU runtime

Payments, store logic, Telegram bots, dream interpretation, runes and unrelated legacy modules stay outside this repository.

## Runtime pipeline

```
Browser microphone
  -> Deepgram STT
  -> Session Manager
  -> Orchestrator
      -> Memory
      -> Astrofractal Engine
      -> Gemini Astro Interpreter
      -> Psychology / Empathy Context
  -> Conversation LLM
  -> TTS Router
      -> Yandex SpeechKit / Ermil (RU)
      -> Microsoft multilingual (other languages)
  -> GPU Avatar Worker
  -> live TELEPAT in browser
```

## Current phase

Phase 1: build the clean integration kernel:

- FastAPI
- Session Manager
- Orchestrator
- LLM Router
- health/chat endpoints

Astrofractal, memory, voice and avatar are added as isolated adapters in later phases.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [ROADMAP.md](ROADMAP.md).
