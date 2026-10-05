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
- `barge_in`
- `reply`
- `audio_start`
- binary MP3 payload
- `audio_end`
- `audio_unavailable`
- `error`

Current path:

```
PCM -> Deepgram -> Orchestrator -> LLM -> Yandex Ermil -> MP3
```

Future avatar path:

```
PCM -> Deepgram -> Orchestrator -> LLM -> TTS
    -> Modal GPU Avatar Worker
    -> synchronized avatar media/stream
```

The browser must persist the returned TELEPAT `user_id` locally and pass it on
future visits. This is a TELEPAT-generated random identity, not browser
fingerprinting.
