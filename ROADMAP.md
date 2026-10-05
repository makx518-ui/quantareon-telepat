# TELEPAT Roadmap

## Phase 0 — Repository foundation
- [x] Create integration repository
- [x] Define product boundary
- [x] Define architecture and orchestration flow
- [x] Add package/configuration skeleton
- [x] Add CI
- [x] Add automated Modal smoke/deployment workflows

## Phase 1 — Minimal backend
Goal: text request -> TELEPAT text response.

- [x] FastAPI app
- [x] health/readiness endpoints
- [x] request/response models
- [x] Session Manager
- [x] Orchestrator
- [x] Context Builder
- [x] replaceable LLM Router
- [x] mock/fallback provider
- [x] Modal CPU deployment
- [x] deployed `/chat` smoke request
- [x] live HTTP smoke after deployment

Runtime status:
- deterministic/core path works in Modal
- real conversation provider waits for provider credentials

## Phase 2 — Astrofractal
Goal: TELEPAT can reason from the current Astrofractal method.

- [x] required donor Astrofractal modules
- [x] deterministic calculation model
- [x] package non-Python Astrofractal data into Modal
- [x] Gemini Astro interpreter
- [x] structured JSON output contract
- [x] session-level AstroSummary cache
- [x] fixed-data engine tests
- [x] cache lifecycle tests
- [x] real deterministic Astrofractal calculation in Modal

Runtime gate:
- [ ] real Gemini Astro interpretation in Modal

## Phase 3 — Psychology
Goal: responses sound like a competent calm astropsychologist.

- [x] state-understanding cues
- [x] psychology context
- [x] empathy/communication layer
- [x] integrator policy
- [x] no unnecessary per-layer LLM calls
- [x] tests

Further tuning should come from real conversation transcripts.

## Phase 4 — Memory
Goal: returning users are recognized through TELEPAT identity and relevant prior
context.

- [x] stable browser `user_id`
- [x] MemoryAdapter protocol boundary
- [x] existing remote Memory API client
- [x] compact relevant context
- [x] asynchronous exchange persistence
- [x] core modules depend on MemoryAdapter rather than concrete remote client
- [x] adapter contract test

Pending after the standalone Memory service is attached:
- [ ] validate production recall/store contract
- [ ] validate any required authentication header
- [ ] tune fact/summary policy from real sessions
- [ ] move shared session state out of in-process memory when scaling beyond one CPU container

## Phase 5 — Voice
Goal: full duplex spoken conversation without GPU avatar rendering.

- [x] Deepgram Nova-3 streaming STT implementation
- [x] multilingual language routing
- [x] interim/final transcripts
- [x] VAD speech-start event
- [x] playback-aware barge-in
- [x] Yandex SpeechKit Ermil
- [x] Microsoft Andrew multilingual fallback
- [x] WebSocket/session audio protocol
- [x] browser PCM16 client
- [x] live Modal WebSocket route smoke
- [x] TTS/barge-in tests

Runtime gates:
- [ ] real Deepgram connection
- [ ] real TTS generation
- [ ] browser microphone -> STT -> LLM -> TTS
- [ ] real interruption test during playback

## Phase 6 — Avatar GPU
Goal: TELEPAT speaks through the final fixed character.

- [x] Modal L4 worker boundary
- [x] scale-to-zero design
- [x] persistent asset-volume boundary
- [x] behavior state library
- [x] deterministic state/director logic
- [x] browser Avatar Controller + `setLiveMedia()`
- [x] CPU deployment decoupled from GPU registration
- [ ] enable L4 access/billing in Modal
- [ ] benchmark candidate lip-sync engines
- [ ] select the winning engine
- [ ] install it behind AvatarAdapter
- [ ] audio -> lip-sync render
- [ ] latency/VRAM measurements

## Phase 7 — Site integration
Goal: production TELEPAT experience in `quantareon-site`.

- [ ] connect existing TELEPAT page to Modal API
- [ ] start bootstrap during greeting video
- [ ] map final idle/listening/thinking/gesture clips
- [ ] connect GPU speaking media
- [ ] reconnect/error UX
- [ ] mobile checks

## Phase 8 — Production hardening
- [x] credentials kept outside repository code
- [x] provider fallbacks at architecture level
- [x] core/provider readiness separation
- [x] automated live HTTP/WebSocket deployment smoke
- [ ] rate limits
- [ ] structured observability/latency metrics
- [ ] privacy/data-retention controls
- [ ] cost counters per session
- [ ] load tests

## Immediate execution order

1. Attach real provider credentials to Modal.
2. Validate Astrofractal -> Gemini -> cached AstroSummary.
3. Validate real conversation LLM through the router.
4. Validate Deepgram -> LLM -> Ermil/Andrew and real barge-in.
5. Attach/validate the existing Memory API.
6. Enable Modal L4 and benchmark avatar/lip-sync candidates.
7. Connect the finished runtime to `quantareon-site`.

## Non-goals for first release

Do not import:

- store/payment code
- dream oracle features
- runes/numerology
- Telegram bot logic
- legacy Amvera keep-alive
- unrelated admin dashboards
- old monolithic server files
