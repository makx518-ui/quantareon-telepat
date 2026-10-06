# TELEPAT Voice Protocol

Endpoint:

```
/ws/voice?user_id=<optional>&session_id=<optional>&language=ru
```

Browser sends:

- binary PCM16 mono audio, 16 kHz
- optional JSON text control:
  - `{"type":"finalize"}`
  - `{"type":"ping"}`
  - `{"type":"playback_end"}` after browser MP3 playback finishes or fails

Server events:

- `ready`
- `transcript`
  - `final: false` for Deepgram interim text
  - `final: true` for the utterance sent to the orchestrator
- `barge_in`
- `reply`
- `audio_start`
- binary MP3 payload
- `audio_end`
- `audio_unavailable`
- `error`

Current path:

```
PCM -> Deepgram Nova-3 -> Orchestrator -> Conversation LLM
    -> TTS Router -> browser MP3
```

Russian TTS policy:

```
Yandex SpeechKit / Ermil
    -> if unavailable or failed:
Microsoft Andrew Multilingual
```

Other supported languages use Microsoft Andrew Multilingual directly.

Future avatar path:

```
PCM -> Deepgram -> Orchestrator -> LLM -> TTS
    -> Modal GPU Avatar Worker
    -> synchronized avatar media/stream
```

Barge-in behavior:

1. Deepgram emits `SpeechStarted`.
2. The server cancels an active response task if generation/TTS is still running.
3. The server also remembers whether delivered audio is still playing in the browser.
4. The browser receives `barge_in` even when generation already finished but MP3 playback is still active.
5. Browser audio playback stops immediately.
6. TELEPAT returns to the listening state.
7. Normal playback completion sends `playback_end` so the server clears the playback flag.

The browser must persist the returned TELEPAT `user_id` locally and pass it on
future visits. This is a TELEPAT-generated random identity, not browser
fingerprinting.


## Automatic language mode

The browser may open the voice socket with `language=auto` (or `multi`).

TELEPAT then requests Deepgram Nova-3 multilingual recognition. For every
utterance it reads the language tags returned by Deepgram and routes that
detected language into both the Conversation LLM and TTS layer.

Routing policy:

```
detected Russian -> Yandex Ermil -> Andrew fallback
other detected language -> Microsoft Andrew Multilingual
```

Nova-3 multilingual currently covers the core TELEPAT auto-language set:
English, Spanish, French, German, Hindi, Russian, Portuguese, Japanese, Italian
and Dutch. The Andrew locale map explicitly covers the same set.

A fixed socket language such as `ru` or `en-US` still disables automatic
selection and keeps that language for the whole voice session.


## Session lifetime limits

The voice server enforces two configurable cost/safety limits:

- `TELEPAT_VOICE_IDLE_TIMEOUT_SECONDS` — closes a silent/idle browser voice
  connection after no incoming audio/control frames for the configured period.
- `TELEPAT_VOICE_MAX_SESSION_SECONDS` — hard ceiling for one voice connection.

Defaults are 120 seconds idle and 1800 seconds total.

Before closing normally, the server sends:

```json
{"type":"session_end","reason":"idle_timeout"}
```

or:

```json
{"type":"session_end","reason":"max_duration"}
```

The browser releases microphone/audio resources, emits
`telepat:session-end`, moves to `stopped`, and may reconnect through the
runtime facade.


## Audio pacing and frame guards

The browser sends PCM16 mono 16 kHz, which is 32,000 bytes of audio per real
second. The server protects the upstream STT stream from accidental or hostile
audio flooding:

- `TELEPAT_VOICE_MAX_FRAME_BYTES` — maximum one binary WebSocket frame
- `TELEPAT_VOICE_MAX_CONTROL_CHARS` — maximum JSON control-frame text size
- `TELEPAT_VOICE_MAX_REALTIME_FACTOR` — maximum sustained audio speed relative
  to wall-clock time
- `TELEPAT_VOICE_AUDIO_BURST_SECONDS` — initial jitter/buffer allowance

Default browser frames are well below these limits. A violation is rejected
before bytes are forwarded to Deepgram and ends the voice session with
`frame_too_large`, `control_too_large` or `audio_rate_limit`.


## Turn correlation

Every final user utterance receives a monotonically increasing `turn_id`
within one voice WebSocket connection.

The same id is carried through:

- final `transcript`
- `state: thinking`
- `reply`
- `audio_start`
- following binary MP3 payload (implicitly bound to that `audio_start`)
- `audio_end`
- turn-scoped `error` / `audio_unavailable`
- `barge_in` for the interrupted turn

Example:

```json
{"type":"reply","turn_id":4,"text":"..."}
{"type":"audio_start","turn_id":4,"format":"mp3"}
<binary MP3>
{"type":"audio_end","turn_id":4}
```

Browser playback completion returns the same id:

```json
{"type":"playback_end","turn_id":4}
```

When barge-in invalidates turn 4, the browser marks all frames for turn 4 (and
any older turn) as stale. A late reply, `audio_start`, binary payload or
`audio_end` from that turn is ignored instead of interrupting the new turn.

The server also derives a unique idempotency key from the WebSocket connection
id plus `turn_id`, so an internal retry of the same voice turn cannot create
a second LLM/history write.
