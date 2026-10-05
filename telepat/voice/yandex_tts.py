from __future__ import annotations

import os

import httpx


class YandexSpeechKitTTS:
    """Russian TELEPAT voice through Yandex SpeechKit API v1."""

    name = "yandex-ermil"
    endpoint = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

    def __init__(self) -> None:
        self.api_key = os.getenv("YANDEX_SPEECHKIT_API_KEY", "")
        self.iam_token = os.getenv("YANDEX_IAM_TOKEN", "")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID", "")
        self.voice = os.getenv("YANDEX_TTS_VOICE", "ermil")
        self.emotion = os.getenv("YANDEX_TTS_EMOTION", "neutral")
        self.speed = os.getenv("YANDEX_TTS_SPEED", "0.96")

    @property
    def configured(self) -> bool:
        return bool(
            self.api_key
            or (self.iam_token and self.folder_id)
        )

    def _authorization(self) -> str:
        if self.api_key:
            return f"Api-Key {self.api_key}"
        if self.iam_token:
            return f"Bearer {self.iam_token}"
        raise RuntimeError("Yandex SpeechKit credentials are not configured")

    async def synthesize(
        self,
        text: str,
        *,
        language: str = "ru",
    ) -> bytes:
        if not self.configured:
            raise RuntimeError("Yandex SpeechKit is not configured")
        if not language.lower().startswith("ru"):
            raise ValueError("Ermil provider supports Russian output only")

        clean = text.strip()
        if not clean:
            return b""
        if len(clean) > 5000:
            clean = clean[:5000]

        form = {
            "text": clean,
            "lang": "ru-RU",
            "voice": self.voice,
            "emotion": self.emotion,
            "speed": self.speed,
            "format": "mp3",
        }
        # API-key authentication uses the service-account folder automatically.
        if not self.api_key and self.folder_id:
            form["folderId"] = self.folder_id

        headers = {"Authorization": self._authorization()}

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                data=form,
            )
            response.raise_for_status()
            return response.content


yandex_tts = YandexSpeechKitTTS()
