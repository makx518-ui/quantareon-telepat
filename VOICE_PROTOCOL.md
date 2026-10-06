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
