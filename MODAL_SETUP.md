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
- `TELEPAT_CONVERSATION_PROVIDER`
- `TELEPAT_CONVERSATION_MODEL`
- `TELEPAT_CONVERSATION_FALLBACKS`
- `TELEPAT_GEMINI_MODEL`
- `TELEPAT_GROQ_MODEL`
- `TELEPAT_OPENAI_MODEL`
- `TELEPAT_CLAUDE_MODEL`
- `TELEPAT_ASTRO_PROVIDER`
- `TELEPAT_ASTRO_MODEL`

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

Calls the deployed `quantareon-telepat::provider_probe` function through
`deploy/run_provider_probe.py`.

The diagnostic logic lives once in
`telepat/diagnostics/provider_probe.py`. It always checks the deterministic
Astrofractal and orchestration kernel. When provider credentials exist it also
makes real Gemini/LLM/TTS/Deepgram checks and fails when a configured required
provider is broken.

The old command `python -m modal run deploy/smoke.py` remains as a compatibility
launcher, but it delegates to the same deployed provider probe rather than
maintaining a second smoke implementation.

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

CPU and GPU are separate Modal Apps:

- `quantareon-telepat` — FastAPI/session/orchestration/provider probe
- `quantareon-telepat-avatar` — L4 avatar worker only

This separation prevents GPU billing/resource constraints from changing the
CPU app object graph or blocking CPU deployment.

L4 deployment is intentionally opt-in through one GitHub/Modal runtime flag:

`TELEPAT_AVATAR_GPU_ENABLED=1`

The deploy workflow always deploys the CPU app and, only when this flag is
true, separately deploys `deploy/avatar_gpu.py`. The same flag is synced into
the runtime secret for production-readiness reporting.

The CPU backend deploys without GPU access while the flag is unset/false. When
enabled, the provider-smoke workflow also runs `deploy/run_avatar_probe.py`,
which looks up the deployed `AvatarGPUWorker` with Modal `Cls.from_name` and
checks real GPU availability/assets without hard-coding a lip-sync engine.

Enable the flag only when L4 access/billing is ready and the avatar benchmark
starts.


## Modal object graph rule

`quantareon-telepat-secrets` is attached unconditionally to CPU functions.
Deployment automation creates the named Secret with a harmless management
marker when no provider credentials exist yet. This keeps Modal function
dependencies identical during local deployment and remote container hydration.

Do not conditionally define Modal Functions, Classes, Secrets or Volumes inside
the CPU app based on environment variables. Optional GPU infrastructure belongs
in the separate avatar app.
