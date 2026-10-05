# TELEPAT Roadmap

## Phase 0 — Repository foundation
- [x] Create integration repository
- [x] Define product boundary
- [x] Define architecture and orchestration flow
- [ ] Add package skeleton and configuration

## Phase 1 — Minimal backend
Goal: text request -> TELEPAT text response.

- FastAPI app
- /health
- request/response models
- Session Manager
- Orchestrator
- Context Builder
- LLM interface + router
- mock/fallback conversation provider
- unit tests

Exit condition:
- Modal can run the app
- /health returns OK
- /chat accepts session/user/message and returns normalized response

## Phase 2 — Astrofractal
Goal: TELEPAT can reason from the new Astrofractal method.

- copy/adapt only required current Astrofractal modules from quantareon-engine
- add missing unique Oracle components where useful
- AstroAdapter
- normalized Astrofractal result
- GeminiAstroInterpreter
- session-level AstroSummary cache
- tests using fixed birth data

Exit condition:
- one deterministic Astrofractal calculation
- one cached Gemini interpretation
- subsequent chat turns reuse summary without unnecessary recalculation

## Phase 3 — Psychology
Goal: responses sound like a competent calm astropsychologist.

- psychological state context
- empathy rules
- communication style
- integrator / response policy
- prompt regression tests

## Phase 4 — Memory
Goal: returning users are recognized by their TELEPAT identity and prior conversation summaries.

- MemoryAdapter protocol
- remote memory client
- Session memory
- emergency/fallback memory
- fact extraction policy
- summary policy

## Phase 5 — Voice
Goal: full duplex spoken conversation without avatar.

- Deepgram streaming STT
- barge-in
- Yandex SpeechKit Ermil
- Microsoft multilingual fallback
- WebSocket/session audio protocol
- browser voice client

Exit condition:
- user speaks
- TELEPAT understands
- TELEPAT responds with audio
- interruption works

## Phase 6 — Avatar GPU
Goal: TELEPAT speaks through the final avatar.

- choose lip-sync/avatar engine after benchmark
- Modal GPU image
- base avatar assets
- behavior state library
- state selector
- audio -> lip sync
- latency measurements

## Phase 7 — Site integration
Goal: production user experience.

- connect quantareon-site TELEPAT page
- greeting video
- silent idle state
- microphone state
- thinking state
- speaking state
- reconnect/error states
- mobile checks

## Phase 8 — Production hardening
- secrets only in Modal/GitHub secret stores
- rate limits
- observability
- privacy/data retention controls
- cost counters per session
- provider fallbacks
- load tests

## Non-goals for first release

Do not import:
- store/payment code
- dream oracle features
- runes/numerology
- Telegram bot logic
- legacy Amvera keep-alive
- unrelated admin dashboards
- old monolithic server files
