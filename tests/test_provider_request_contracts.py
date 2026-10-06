import asyncio

import telepat.llm.claude as claude_module
import telepat.llm.groq as groq_module
import telepat.llm.openai as openai_module
import telepat.voice.microsoft_tts as microsoft_module
import telepat.voice.yandex_tts as yandex_module
from telepat.core.models import ContextPacket


class _Response:
    def __init__(
        self,
        payload: dict | None = None,
        *,
        content: bytes = b"",
        status_code: int = 200,
    ) -> None:
        self._payload = payload or {}
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _CaptureClient:
    response = _Response()
    calls: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        type(self).calls = []
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, **kwargs):
        type(self).calls.append(
            {
                "url": url,
                **kwargs,
            }
        )
        return type(self).response


def _context() -> ContextPacket:
    return ContextPacket(
        session_id="s",
        user_id="u",
        language="ru",
        current_message="Привет",
        intent="casual_conversation",
    )


def test_openai_request_contract(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setattr(
        openai_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Ответ",
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
            },
        }
    )

    result = asyncio.run(
        openai_module.OpenAIConversationProvider().generate(
            _context()
        )
    )

    call = _CaptureClient.calls[0]
    assert call["url"] == "https://api.openai.com/v1/responses"
    assert call["headers"]["Authorization"] == "Bearer openai-test"
    assert call["json"]["store"] is False
    assert call["json"]["max_output_tokens"] == 1200
    assert call["json"]["model"]
    assert "Привет" in call["json"]["input"]
    assert result.text == "Ответ"


def test_groq_request_contract(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "groq-test")
    monkeypatch.setattr(
        groq_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(
        {
            "choices": [
                {
                    "message": {
                        "content": "Ответ Groq",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
            },
        }
    )

    result = asyncio.run(
        groq_module.GroqConversationProvider().generate(
            _context()
        )
    )

    call = _CaptureClient.calls[0]
    assert (
        call["url"]
        == "https://api.groq.com/openai/v1/chat/completions"
    )
    assert call["headers"]["Authorization"] == "Bearer groq-test"
    assert call["json"]["max_completion_tokens"] == 1200
    assert call["json"]["temperature"] == 0.55
    assert call["json"]["messages"]
    assert result.text == "Ответ Groq"


def test_claude_request_contract(monkeypatch) -> None:
    class _Settings:
        claude_model = "claude-test-model"

        @staticmethod
        def model_for(provider: str, provider_default: str) -> str:
            return provider_default

    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-test")
    monkeypatch.setattr(claude_module, "settings", _Settings())
    monkeypatch.setattr(
        claude_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(
        {
            "content": [
                {
                    "type": "text",
                    "text": "Ответ Claude",
                }
            ],
            "usage": {
                "input_tokens": 20,
                "output_tokens": 4,
            },
        }
    )

    result = asyncio.run(
        claude_module.ClaudeConversationProvider().generate(
            _context()
        )
    )

    call = _CaptureClient.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "claude-test"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["json"]["model"] == "claude-test-model"
    assert call["json"]["max_tokens"] == 1200
    assert call["json"]["system"]
    assert "Привет" in call["json"]["messages"][0]["content"]
    assert result.text == "Ответ Claude"


def test_yandex_api_key_request_contract(monkeypatch) -> None:
    monkeypatch.setenv("YANDEX_SPEECHKIT_API_KEY", "yandex-test")
    monkeypatch.delenv("YANDEX_IAM_TOKEN", raising=False)
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)
    monkeypatch.setattr(
        yandex_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(content=b"mp3")

    provider = yandex_module.YandexSpeechKitTTS()
    audio = asyncio.run(
        provider.synthesize("Привет", language="ru")
    )

    call = _CaptureClient.calls[0]
    assert call["url"].endswith("/speech/v1/tts:synthesize")
    assert call["headers"]["Authorization"] == "Api-Key yandex-test"
    assert call["data"]["voice"] == "ermil"
    assert call["data"]["lang"] == "ru-RU"
    assert call["data"]["format"] == "mp3"
    assert "folderId" not in call["data"]
    assert audio == b"mp3"


def test_yandex_iam_request_contract(monkeypatch) -> None:
    monkeypatch.delenv("YANDEX_SPEECHKIT_API_KEY", raising=False)
    monkeypatch.setenv("YANDEX_IAM_TOKEN", "iam-test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "folder-test")
    monkeypatch.setattr(
        yandex_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(content=b"mp3")

    provider = yandex_module.YandexSpeechKitTTS()
    asyncio.run(
        provider.synthesize("Привет", language="ru")
    )

    call = _CaptureClient.calls[0]
    assert call["headers"]["Authorization"] == "Bearer iam-test"
    assert call["data"]["folderId"] == "folder-test"


def test_microsoft_request_contract_and_ssml_escape(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_SPEECH_KEY", "azure-test")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    monkeypatch.setattr(
        microsoft_module.httpx,
        "AsyncClient",
        _CaptureClient,
    )
    _CaptureClient.response = _Response(content=b"mp3")

    provider = microsoft_module.MicrosoftMultilingualTTS()
    audio = asyncio.run(
        provider.synthesize(
            "Привет <мир>",
            language="ru",
        )
    )

    call = _CaptureClient.calls[0]
    assert call["url"] == (
        "https://westeurope.tts.speech.microsoft.com/"
        "cognitiveservices/v1"
    )
    assert (
        call["headers"]["Ocp-Apim-Subscription-Key"]
        == "azure-test"
    )
    assert (
        call["headers"]["X-Microsoft-OutputFormat"]
        == "audio-24khz-48kbitrate-mono-mp3"
    )
    ssml = call["content"].decode("utf-8")
    assert 'xml:lang="ru-RU"' in ssml
    assert "en-US-AndrewMultilingualNeural" in ssml
    assert 'style="empathetic"' in ssml
    assert "Привет &lt;мир&gt;" in ssml
    assert audio == b"mp3"
