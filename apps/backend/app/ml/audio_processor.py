import openai
import base64
import tempfile
import os

client = openai.AsyncOpenAI()


async def transcribe_audio(audio_b64: str) -> dict:
    audio_bytes = base64.b64decode(audio_b64)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=open(tmp_path, "rb"),
            response_format="verbose_json",
        )
        return {
            "transcript": result.text,
            "confidence": getattr(result, "avg_logprob", 0.8),
        }
    finally:
        os.unlink(tmp_path)
