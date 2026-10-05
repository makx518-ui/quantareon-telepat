# Modal setup

TELEPAT uses one named Modal Secret for external credentials.

Create it locally after `modal setup`:

    modal secret create quantareon-telepat-secrets \
      GEMINI_API_KEY=... \
      GROQ_API_KEY=... \
      DEEPGRAM_API_KEY=... \
      YANDEX_SPEECHKIT_API_KEY=... \
      YANDEX_FOLDER_ID=... \
      MEMORY_API_URL=...

Only include keys that are currently used. The secret can be updated later.

Do not commit a real `.env` file or credentials to GitHub.

Deployment entrypoint:

    modal deploy deploy/modal_app.py

Development run:

    modal serve deploy/modal_app.py

The CPU web function and future GPU avatar worker belong to the same Modal App:
`quantareon-telepat`.
