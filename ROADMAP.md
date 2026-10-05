# TELEPAT Roadmap

## Phase 0 — Repository foundation
- [x] Create integration repository
- [x] Define product boundary
- [x] Define architecture and orchestration flow
- [x] Add package skeleton and configuration
- [x] Add CI

## Phase 1 — Minimal backend
Goal: text request -> TELEPAT text response.

- [x] FastAPI app
- [x] `/health`
- [x] request/response models
- [x] Session Manager
- [x] Orchestrator
- [x] Context Builder
- [x] LLM interface + replaceable router
- [x] mock/fallback provider
- [x] unit tests
- [x] Modal CPU application definition

Runtime gate:
- [ ] real provider smoke in Modal
- [ ] deployed `/chat` smoke request

## Phase 2 — Astrofractal
Goal: TELEPAT can reason from the current Astrofractal method.

- [x] required Astrofractal modules copied/adapted from donor engine
- [x] normalized calculation model
- [x] Gemini Astro interpreter
- [x] structured JSON output contract
- [x] session-level AstroSummary cache
- [x] fixed-data engine tests
- [x] cache lifecycle tests

Runtime gate:
- [ ] real Gemini Astro call in Modal

## Phase 3 — Psychology
Goal: responses sound like a competent calm astropsychologist.

- [x] state-understanding context
- [x] psychology context
- [x] empathy/communication layer
- [x] integrator policy
- [x] tests

Further tuning will be based on real conversation transcripts rather than
adding separate expensive LLM calls per layer.

## Phase 4 — Memory
Goal: returning users are recognized by TELEPAT identity and relevant prior
context.

- [x] MemoryAdapter boundary
- [x] existing remote Memory API client
- [x] stable browser `user_id`
- [x] session memory
- [x] compact relevant context
- [x] asynchronous exchange persistence

Pending after the standalone Memory service is attached:
- [ ] validate remote recall/store contract against production server
- [ ] tune fact/summary policy from real sessions

## Phase 5 — Voice
Goal: full duplex spoken conversation without GPU avatar rendering.

- [x] Deepgram Nova-3 streaming STT
- [x] interim/final transcripts
- [x] barge-in
- [x] Yandex SpeechKit Ermil
- [x] Microsoft Andrew multilingual fallback
- [x] WebSocket/session audio protocol
- [x] browser PCM16 client
- [x] TTS fallback tests

Runtime gate:
- [ ] real Deepgram connection in Modal
- [ ] real TTS generation in Modal
- [ ] browser microphone -> STT -> LLM -> TTS smoke
- [ ] interruption test with real playback

## Phase 6 — Avatar GPU
Goal: TELEPAT speaks through the final fixed character.

- [x] Modal L4 GPU boundary
- [x] scale-to-zero configuration
- [x] persistent asset volume boundary
- [x] behavior state library
- [x] deterministic state/director logic
- [x] browser Avatar Controller and `setLiveMedia()` boundary
- [ ] benchmark candidate lip-sync engines
- [ ] select engine after benchmark
- [ ] install selected engine in GPU image
- [ ] audio -> lip-sync render
- [ ] latency/VRAM measurements

## Phase 7 — Site integration
Goal: production TELEPAT experience in `quantareon-site`.

- [ ] connect existing TELEPAT page to Modal API
- [ ] run bootstrap during greeting video
- [ ] map final idle/listening/thinking/gesture clips
- [ ] connect GPU speaking media
- [ ] reconnect/error UX
- [ ] mobile checks

## Phase 8 — Production hardening
- [x] secrets excluded from repository
- [x] provider fallbacks at architecture level
- [ ] rate limits
- [ ] observability
- [ ] privacy/data retention controls
- [ ] cost counters per session
- [ ] load tests

## Immediate execution order

1. Run private Modal provider smoke (`modal run deploy/smoke.py`).
2. Fix any real Gemini/LLM/TTS/Deepgram provider incompatibility.
3. Run deployed `/chat` and browser `/ws/voice` end-to-end.
4. Benchmark avatar/lip-sync candidates on L4.
5. Fix the winning GPU engine behind the existing AvatarAdapter boundary.
6. Integrate the finished runtime into `quantareon-site`.

## Non-goals for first release

Do not import:

- store/payment code
- dream oracle features
- runes/numerology
- Telegram bot logic
- legacy Amvera keep-alive
- unrelated admin dashboards
- old monolithic server files
