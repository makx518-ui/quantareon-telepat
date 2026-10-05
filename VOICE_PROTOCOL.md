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
2. The server cancels the current response task.
3. The browser receives `barge_in`.
4. Browser audio playback stops immediately.
5. TELEPAT returns to the listening state.

The browser must persist the returned TELEPAT `user_id` locally and pass it on
future visits. This is a TELEPAT-generated random identity, not browser
fingerprinting.
