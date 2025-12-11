"""
Модуль TTS-клиента для Алины.

Здесь мы аккуратно переиспользуем уже готовую функцию tts_elevenlabs
из файла elevenlabs_client.py, чтобы не дублировать код.
"""

import base64
from elevenlabs_client import tts_elevenlabs


def synthesize_voice(text: str) -> bytes:
    """
    Обёртка над tts_elevenlabs, чтобы в остальном коде
    использовать единое имя synthesize_voice.

    Предполагаем, что tts_elevenlabs возвращает байты аудио (mp3/ogg/etc.).
    """
    return tts_elevenlabs(text)


def text_to_speech_base64(text: str) -> str:
    """
    Унифицированный helper для Алины.

    На вход: текст.
    На выход: base64-строка с аудио (которую фронт кладёт в audio.src).
    """
    audio_bytes = synthesize_voice(text)

    # На случай, если tts_elevenlabs вернёт строку:
    if isinstance(audio_bytes, str):
        audio_bytes = audio_bytes.encode("utf-8")

    return base64.b64encode(audio_bytes).decode("utf-8")
