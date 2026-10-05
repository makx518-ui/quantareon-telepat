# Modal setup

TELEPAT uses one named Modal Secret for external provider credentials:
`quantareon-telepat-secrets`.

It may contain only the providers currently in use, for example:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `DEEPGRAM_API_KEY`
- `YANDEX_SPEECHKIT_API_KEY`
- `YANDEX_FOLDER_ID`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `MEMORY_API_URL`
- `MEMORY_API_KEY`

Never commit real credentials or a populated `.env` file.

## Preferred path: GitHub Actions -> Modal

Local Modal CLI setup is not required for normal TELEPAT validation.

Repository Actions secrets required once:

- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

Then run:

`Actions -> TELEPAT Modal Smoke -> Run workflow`

The workflow `.github/workflows/modal-smoke.yml` authenticates to Modal using
those GitHub Secrets and runs:

    python -m modal run deploy/smoke.py

Provider credentials stay in the Modal Secret
`quantareon-telepat-secrets`; the GitHub workflow only needs the two Modal
authentication values.

## Provider smoke test

The private smoke function checks:

- deterministic Astrofractal + real Gemini Astro interpretation;
- a real orchestrated conversation turn;
- Russian TTS routing (Ermil, with Andrew fallback);
- a real Deepgram WebSocket connection.

It returns only provider names, success flags and payload sizes. It does not
print or return secret values.

This is intentionally a CI/CLI smoke test, not a public FastAPI debug endpoint.

## Deployment

Production deployment entrypoint:

    modal deploy deploy/modal_app.py

Development fallback, if local Modal CLI is intentionally configured:

    modal serve deploy/modal_app.py

The CPU web function and the L4 GPU avatar worker belong to the same Modal App:
`quantareon-telepat`.
