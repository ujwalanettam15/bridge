async def transcribe_audio(audio_b64: str) -> dict:
    # OpenRouter is chat-completions compatible, but it does not provide speech-to-text.
    # Keep audio optional until a separate STT provider is added.
    return {"transcript": "", "confidence": 0, "status": "stt_unconfigured"}
