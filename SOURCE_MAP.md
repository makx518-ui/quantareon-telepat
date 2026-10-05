# TELEPAT Source Map

This file records where each subsystem should come from. The goal is reuse, not rewriting.

## 1. quantareon-site

Use for:
- TELEPAT page shell
- visual language and responsive layout
- greeting video integration
- browser-side microphone / avatar UI hooks

Do not import:
- payments
- store pages
- unrelated essays or product flows

## 2. quantareon-engine

Primary source of deterministic astrology.

Use for:
- current Astrofractal implementation
- natal basis required by Astrofractal
- Swiss Ephemeris integration
- current location/time calculations that Astrofractal needs
- existing FastAPI patterns where useful

Important rule:
- TELEPAT does not import the whole existing API application.
- Copy or package only the calculation modules needed by AstroAdapter.

## 3. QUANTARION Platform archive

Primary source of conversation infrastructure.

Use for:
- orchestration ideas
- ConsciousAI / four-voice logic where it improves response quality
- Deepgram streaming STT
- voice session management
- barge-in / interruption behavior
- WebSocket voice transport
- emergency/fallback memory patterns
- provider routing/fallback ideas

Do not import:
- monolithic server.py
- old Amvera keep-alive
- unrelated assistants/tools/admin logic

## 4. Dream Oracle archive

Primary source of Astrofractal interpretation glue and selected fallbacks.

Use for:
- quantareon_bridge patterns
- unique Astrofractal modules absent from quantareon-engine
- interpretation methodology/prompts
- Groq key rotation/fallback patterns
- optional Whisper fallback
- Microsoft multilingual TTS ideas

Do not import:
- dream interpretation product
- runes/numerology
- payments
- Telegram bot logic
- Oracle monolith

## 5. Existing remote Memory service

Do not copy yet.

Integrate through telepat.memory.MemoryAdapter:
- recall user profile
- recall summaries/facts
- store turn
- store fact
- store summary

This lets the memory backend be repaired or replaced without changing TELEPAT core.

## 6. New code written specifically for TELEPAT

Only these layers should be genuinely new:
- normalized data models
- Session Manager facade
- Context Packet
- central Orchestrator
- adapter interfaces
- LLM Router facade
- Modal CPU/GPU deployment split
- avatar state selector
- integration tests

Everything else should reuse proven donor code where technically sound.
