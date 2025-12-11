import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_audio(audio_bytes: bytes, filename: str):
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes)
    )
    return response.text
