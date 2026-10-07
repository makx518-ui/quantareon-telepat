from __future__ import annotations

import json
from pathlib import Path

import modal


APP_NAME = "quantareon-telepat-video-skyreels"
WORKER_CLASS = "SkyReelsV3Worker"

PROMPT = """
Photorealistic cinematic talking avatar in the exact provided QUANTAREON cabinet.
Preserve the man's identity exactly: same face, beard, hair, age, skin texture,
body proportions, clothing, hat, vest and chain. Preserve the cabinet, chair,
desk, ashtray, cigar box, lighting, colors and spatial composition.
He remains seated naturally in the same leather chair behind the desk.
He speaks the supplied Russian audio naturally with precise lip synchronization.
Calm, intelligent, warm, confident psychologist and philosopher.
He looks mostly directly at the viewer. Natural blinking, subtle breathing,
tiny realistic head movements. Very restrained body movement.
Occasional small hand movement only if natural; no exaggerated gestures.
Hands and fingers must remain anatomically correct.
Camera is static for this 5-second validation sample.
Warm cinematic golden ambient light, realistic facial illumination and shadows.
High realism. Natural skin, eyes, lips and teeth.
No beauty-filter look. No plastic skin. No fantasy transformation.
No morphing. No change of identity. No change of clothes.
No change of furniture. No change of room geometry.
No new objects appearing or disappearing. No subtitles or generated text.
""".strip()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    image_path = root / "test_assets" / "telepat-master-test.jpg"
    audio_path = root / "test_assets" / "telepat-greeting-5s.mp3"
    output = root / "telepat-skyreels-custom-5s.mp4"

    image = image_path.read_bytes()
    audio = audio_path.read_bytes()

    worker_cls = modal.Cls.from_name(APP_NAME, WORKER_CLASS)
    worker = worker_cls()

    data = worker.render_talking_avatar.remote(
        image=image,
        audio=audio,
        prompt=PROMPT,
        resolution="480P",
        seed=42,
        low_vram=False,
    )
    if not isinstance(data, bytes) or not data:
        raise RuntimeError("SkyReels custom sample returned no media")
    output.write_bytes(data)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "bytes": len(data),
        "reference": str(image_path),
        "audio": str(audio_path),
        "resolution": "480P",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
