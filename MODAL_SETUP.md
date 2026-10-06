# Modal setup

TELEPAT is deployed and tested through GitHub Actions. Local Modal CLI setup is
not required for the normal development path.

## GitHub -> Modal authentication

Repository Actions secrets:

- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

Workflows normalize the stored values before passing them to Modal.

## Provider credentials

Real AI/voice/memory providers belong in one Modal Secret named:

`quantareon-telepat-secrets`

Supported environment names include:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEEPGRAM_API_KEY`
- `YANDEX_SPEECHKIT_API_KEY`
- `YANDEX_IAM_TOKEN`
- `YANDEX_FOLDER_ID`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `MEMORY_API_URL`
- `MEMORY_API_KEY`
- `TELEPAT_OPENAI_MODEL`
- `TELEPAT_CLAUDE_MODEL`

The provider secret is optional at deployment time. Modal workflows detect
whether it exists:

- absent -> deterministic core and fallback behavior are tested
- present -> the runtime attaches it automatically and tests configured providers

The repository also contains **TELEPAT Modal Provider Sync**. It merges non-empty
GitHub Actions secrets into the named Modal Secret using Modal's dict-update
semantics. Existing Modal keys not included in a sync are left unchanged.

The sync covers provider credentials plus runtime policy such as CORS, model
routing, voice tuning, Memory privacy switches, rate limits, session limits and
cost-accounting configuration.

Important: Modal Secret updates are visible only to containers started after the
update. After changing provider/runtime configuration, run a TELEPAT Modal
Deploy (or otherwise restart the runtime) before validating readiness.

## GitHub Actions

### TELEPAT CI

Runs compileall and pytest on Python 3.12.

### TELEPAT Modal Provider Sync

Runs `deploy/sync_modal_provider_secret.py` and merge-updates
`quantareon-telepat-secrets`. It never prints secret values.

### TELEPAT Modal Smoke

Runs `deploy/smoke.py` inside Modal.

Always checks the deterministic Astrofractal and orchestration kernel. When
provider credentials exist it also makes real Gemini/LLM/TTS/Deepgram checks
and fails when a configured required provider is broken.

### TELEPAT Modal Deploy

Deploys the FastAPI application and then runs:

- `deploy/live_api_smoke.py`
- `deploy/live_voice_smoke.py`
- `deploy/live_load_smoke.py`

The current development endpoint is:

`https://makx518--quantareon-telepat-web.modal.run`

The live smoke verifies health/readiness, session bootstrap, chat and the real
WebSocket route.

## CPU runtime

The CPU application contains:

- FastAPI
- Session Manager
- Orchestrator
- Astrofractal
- LLM Router
- MemoryAdapter
- Deepgram/TTS orchestration

Until shared/persistent session state is attached, the Modal web function uses
`max_containers=1` so one TELEPAT session is not split across separate
in-memory processes.

## GPU runtime

L4 registration is intentionally opt-in:

`TELEPAT_REGISTER_GPU=1`

The CPU backend deploys without GPU access. This prevents L4 billing/account
requirements from blocking development of the conversation and voice stack.

Enable GPU registration only when L4 access is ready and the lip-sync benchmark
starts.
