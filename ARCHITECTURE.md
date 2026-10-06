# TELEPAT Architecture

## 1. Goal

TELEPAT is a live AI astropsychologist. The system must remain modular: calculation, memory, psychology, conversation, voice and avatar animation are separate layers coordinated by one orchestrator.

The orchestrator is the control plane. It decides what context is needed for a specific turn and prevents every subsystem from running on every message.

---

## 2. End-to-end flow

```
User
  |
  v
Frontend / microphone
  |
  v
STT (Deepgram)
  |
  v
SessionStore
  |
  v
Orchestrator
  |----> Memory Adapter
  |----> Astrofractal Adapter
  |          |
  |          v
  |       Gemini Astro Interpreter
  |
  |----> Psychology Context
  |
  v
Context Packet
  |
  v
Conversation LLM
  |
  v
Response Policy
  |
  v
TTS Router
  |
  v
Avatar State Selector
  |
  v
GPU Avatar Worker
  |
  v
Browser playback / stream
```

---

## 3. Session lifecycle

### Session start

1. Browser obtains or restores a non-identifying TELEPAT user id.
2. SessionStore creates a session.
3. Memory Adapter loads known user facts and previous summaries.
4. If birth data is available, Astrofractal is calculated once.
5. Gemini creates a compact AstroSummary.
6. Session stores the summary for reuse.
7. Greeting video can play while steps 3-6 execute.

### Conversation turn

1. STT provides text.
2. Orchestrator classifies turn intent.
3. Orchestrator chooses only required context sources.
4. Context Builder creates a compact Context Packet.
5. Conversation LLM writes the answer.
6. Response Policy checks tone, repetition, length and boundaries.
7. TTS produces audio.
8. Avatar State Selector chooses idle / nod / think / gesture state.
9. GPU worker performs lip sync and returns media/stream.
10. Session stores the turn; memory is updated asynchronously when appropriate.

---

## 4. Orchestrator responsibilities

The orchestrator must NOT contain astrology, TTS, memory storage or avatar logic.

It only decides:

- what the user is asking;
- what context is needed now;
- whether AstroSummary is enough or recalculation is required;
- whether memory should be recalled;
- which LLM role should handle the task;
- what avatar state should accompany the response;
- what data should be saved after the turn.

### Initial intent classes

- casual_conversation
- personal_reflection
- astropsychology
- follow_up_astro
- factual_user_memory
- system_action
- unknown

The first implementation should be deterministic and small. LLM-based routing can be added later only if needed.

---

## 5. Context Packet

The conversational model receives one normalized object:

```json
{
  "session": {},
  "user_memory": {},
  "astro_summary": {},
  "psychology": {},
  "conversation_history": [],
  "current_message": "",
  "response_style": {}
}
```

The LLM never needs raw database objects or the complete Astrofractal payload unless explicitly required.

---

## 6. AI roles

### Gemini Astro

Purpose: transform deterministic Astrofractal output into a compact astropsychological interpretation.

It is not the visible conversational personality.

### Conversation LLM

Purpose: speak as TELEPAT using the Context Packet.

Provider must be replaceable through an LLM Router.

Candidate providers:
- Gemini
- OpenAI
- Groq
- Claude-compatible provider
- future Copilot-compatible integration if technically and contractually appropriate

---

## 6.1 Response Policy

The visible LLM reply passes through one deterministic Response Policy before
it is committed to session history or sent to TTS/avatar.

The policy does not make another LLM call. It:

- rejects empty/unusable model output;
- normalizes line endings and excessive blank lines;
- removes consecutive duplicate paragraphs;
- bounds live-dialogue response length with sentence-aware truncation;
- maps unusable provider output into the normal controlled conversation outage
  path rather than storing or voicing invalid content.

The production length ceiling is configured by
`TELEPAT_MAX_REPLY_CHARS`.

## 7. Psychology layers

Keep the first version compact.

1. **State understanding** — what concern/emotion is visible in the current turn.
2. **Psychological framing** — interpret the problem without overclaiming.
3. **Empathic communication** — tone, pacing, wording.
4. **Integrator** — final consistency and boundaries.

These layers should usually enrich one prompt/context rather than trigger four separate expensive model calls.

---

## 8. Memory and session state

Long-term user memory and live session state are separate boundaries.

### MemoryAdapter

The orchestrator uses one stable interface:

```
recall(user_id, message, level)
store_exchange(user_id, message, response_text)
probe()
```

The current implementation is the remote QUANTARION Memory API adapter.
Authentication and privacy switches remain outside the orchestrator.

### SessionStore

Live conversation history, AstroSummary cache, compact recalled memory and
idempotent chat responses are behind `SessionStore`.

The current implementation is bounded in-process storage. Runtime callers depend
only on `telepat.core.session_service.session_store`, so a future shared store
can replace the binding without changing API/orchestration code.

Existing sessions require both matching `session_id` and `user_id` to be
reused. Browser storage may hold only UI state and the anonymous TELEPAT user id.

---

## 9. Voice

### Input

Browser PCM16/16 kHz -> Deepgram Nova-3 streaming STT -> complete utterance.

The voice session handles:

- interim vs final utterance assembly;
- per-utterance language detection in auto mode;
- VAD-driven barge-in;
- upstream STT disconnect cleanup;
- idle and maximum session lifetime;
- binary frame/control size limits;
- wall-clock PCM pacing guards so accelerated audio floods never reach Deepgram.

### Output

Text -> TTS Router.

Initial providers:

- RU: Yandex SpeechKit / Ermil
- multilingual/fallback: Microsoft Andrew Multilingual

Voice providers implement one common interface.

---

## 10. Avatar

The avatar subsystem is isolated from conversational AI.

Inputs:
- final audio
- avatar base/state
- optional expression/state metadata

Outputs:
- generated media or live stream

Initial state library:
- idle
- listening
- thinking
- nod
- hand_chin
- light_gesture
- lean_forward
- soft_smile

Modal GPU worker runs only the expensive animation/lip-sync path.

---

## 11. Modal deployment

TELEPAT deliberately uses two independent Modal Apps.

### `quantareon-telepat` — CPU

- FastAPI
- SessionStore binding
- orchestration
- LLM Router
- deterministic Astrofractal + Gemini interpreter
- MemoryAdapter
- Deepgram/TTS orchestration
- deployed provider diagnostics

The named Secret `quantareon-telepat-secrets` is attached unconditionally so
Modal's function dependency graph is identical during local deployment and
remote hydration.

### `quantareon-telepat-avatar` — GPU

- optional L4 worker
- persistent benchmark/assets Volume
- lip-sync engine behind AvatarAdapter
- hardware/assets preflight
- benchmark harness

GPU deployment is opt-in and cannot change or block the CPU app object graph.

---

## 12. Source projects

The source projects remain untouched.

- quantareon-site
- quantareon-engine
- QUANTARION Platform archive
- Dream Oracle archive

TELEPAT copies only proven modules or wraps them through adapters. No legacy monolith is imported wholesale.


## 13. Idempotent chat requests

HTTP chat requests may include `request_id`.

Within one session:

- the same `request_id` + same normalized payload returns the cached response;
- no second LLM call or second history write occurs;
- reusing the same `request_id` for a different message/language/metadata
  returns HTTP 409 `idempotency_key_conflict`;
- the idempotency cache is bounded LRU and expires with the session.
