from __future__ import annotations

import html
import os

import httpx


_LOCALES = {
    "en": "en-US",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
    "it": "it-IT",
    "pt": "pt-BR",
    "pl": "pl-PL",
    "tr": "tr-TR",
    "uk": "uk-UA",
    "ka": "ka-GE",
}


class MicrosoftMultilingualTTS:
    """Official Azure Speech multilingual TELEPAT voice."""

    name = "microsoft-andrew"

    def __init__(self) -> None:
        self.key = os.getenv("AZURE_SPEECH_KEY", "")
        self.region = os.getenv("AZURE_SPEECH_REGION", "")
        self.voice = os.getenv(
            "AZURE_TTS_VOICE",
            "en-US-AndrewMultilingualNeural",
        )
        self.style = os.getenv("AZURE_TTS_STYLE", "empathetic")

    @property
    def configured(self) -> bool:
        return bool(self.key and self.region)

    @property
    def endpoint(self) -> str:
        return (
            f"https://{self.region}.tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )

    @staticmethod
    def _locale(language: str) -> str:
        value = (language or "en").strip()
        if "-" in value:
            return value
        return _LOCALES.get(value.lower(), "en-US")

    def _ssml(self, text: str, *, language: str) -> str:
        locale = self._locale(language)
        safe_text = html.escape(text.strip())
        safe_voice = html.escape(self.voice, quote=True)
        safe_style = html.escape(self.style, quote=True)

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" '
            f'xml:lang="{locale}">'
            f'<voice name="{safe_voice}">'
            f'<mstts:express-as style="{safe_style}">'
            f'<lang xml:lang="{locale}">{safe_text}</lang>'
            '</mstts:express-as>'
            '</voice>'
            '</speak>'
        )

    async def synthesize(
        self,
        text: str,
        *,
        language: str = "en",
    ) -> bytes:
        if not self.configured:
            raise RuntimeError("Azure Speech is not configured")

        clean = text.strip()
        if not clean:
            return b""

        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "quantareon-telepat",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                content=self._ssml(clean, language=language).encode("utf-8"),
            )
            response.raise_for_status()
            return response.content


microsoft_tts = MicrosoftMultilingualTTS()
