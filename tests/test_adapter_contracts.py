from telepat.astro.adapter import AstroAdapter
from telepat.astro.service import astro_service
from telepat.core.session_service import session_store
from telepat.core.session_store import SessionStore
from telepat.voice.deepgram import DeepgramStreamingSTT
from telepat.voice.interfaces import StreamingSTTProvider, TTSProvider
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.yandex_tts import yandex_tts


def test_astro_service_implements_adapter_contract() -> None:
    assert isinstance(astro_service, AstroAdapter)


def test_deepgram_implements_streaming_stt_contract() -> None:
    stt = DeepgramStreamingSTT(language="ru")
    assert isinstance(stt, StreamingSTTProvider)


def test_tts_providers_implement_common_contract() -> None:
    assert isinstance(yandex_tts, TTSProvider)
    assert isinstance(microsoft_tts, TTSProvider)



def test_session_store_implements_contract() -> None:
    assert isinstance(session_store, SessionStore)
    assert session_store.kind == "in_process"
