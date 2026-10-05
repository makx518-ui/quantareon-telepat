# TELEPAT Avatar Behavior

The avatar is intentionally restrained. It is an astropsychologist, not a
presenter or influencer.

## Runtime phases

1. **idle** — user has not started speaking
2. **listening** — microphone/STT is receiving user speech
3. **thinking** — orchestration/LLM/TTS preparation
4. **speaking** — lip-sync on a calm base clip
5. optional restrained gesture state for some responses

## Gesture library

Initial Vidu/reference states:

- `idle`
- `listening`
- `thinking`
- `nod`
- `hand_chin`
- `light_gesture`
- `lean_forward`
- `soft_smile`
- `speaking`

The final library may contain several clips per state.

## Rules

- camera stays locked
- speaking does not imply body movement
- gestures are occasional, not continuous
- emotional intensity stays low unless product design explicitly changes it
- no random large hand movements
- identity, hat, chair and background remain stable
- the director does not call an LLM just to choose a gesture

For reproducibility and testing, the first AvatarDirector chooses occasional
gestures deterministically from session/message/response content.

Later the director may use sentence-level semantic cues, but its output remains
a small state command rather than model-specific animation instructions.
