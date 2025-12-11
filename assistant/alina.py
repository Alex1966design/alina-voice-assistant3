from __future__ import annotations

from typing import List, Dict, Any

from . import stt_client, llm_client, tts_client


class AlinaAssistant:
    """
    Alina — premium voice sales assistant with two modes:
    - ru: Russian persona
    - en: English persona

    Pipeline:
    1) STT -> user text
    2) LLM -> Alina's answer with dialogue memory
    3) TTS -> audio answer (base64) for the frontend player
    """

    def __init__(self, mode: str = "en", max_history_turns: int = 6) -> None:
        if mode not in ("ru", "en"):
            raise ValueError("mode must be 'ru' or 'en'")
        self.mode = mode

        # Dialogue history as a list of {"role": "user"/"assistant", "content": "..."}
        self.history: List[Dict[str, str]] = []
        # How many last turns (user+assistant pairs) we keep
        self.max_history_turns = max_history_turns

    # ---------- Persona and style of Alina ----------

    @property
    def system_prompt(self) -> str:
        """
        Return system prompt depending on the mode (ru / en).
        """
        if self.mode == "en":
            return (
                "You are Alina, a premium ENGLISH-SPEAKING voice sales assistant.\n\n"
                "LANGUAGE RULES:\n"
                "• You MUST ALWAYS answer in English only.\n"
                "• Even if the user speaks Russian or mixes languages, your reply must be fully in English.\n"
                "• Do NOT switch to Russian. Do NOT mix languages in one answer.\n\n"
                "ROLE:\n"
                "1) Identify the client's needs by asking clear, focused questions.\n"
                "2) Propose solutions, pricing options and next steps so that the client feels care and expertise.\n"
                "3) Explain complex things in a simple, human and friendly way.\n\n"
                "STYLE:\n"
                "• Tone: friendly, confident, professional.\n"
                "• Structure your answers: short summary first, then 3–5 bullet points with details.\n"
                "• Avoid bureaucratic language and clichés.\n"
                "• Be proactive: suggest the next step, ask clarifying questions.\n"
            )

        # Russian persona (mode == "ru")
        return (
            "Ты — Алина, премиальный голосовой нейро-продавец и ассистент по продажам.\n\n"
            "ЯЗЫК:\n"
            "• Всегда отвечай по-русски.\n"
            "• Даже если пользователь говорит по-английски или смешивает языки, твой ответ должен быть полностью на русском.\n\n"
            "РОЛЬ:\n"
            "1) Выяснять потребности клиента, задавая уточняющие вопросы.\n"
            "2) Подбирать решения и варианты так, чтобы клиент чувствовал заботу и экспертность.\n"
            "3) Объяснять сложные вещи простым, живым, человеческим языком.\n\n"
            "СТИЛЬ:\n"
            "• Тон — доброжелательный, уверенный, профессиональный.\n"
            "• Структурируй ответы: краткий вывод, затем 3–5 пунктов с подробностями.\n"
            "• Избегай канцелярита и штампованных фраз.\n"
            "• Будь проактивной: предлагай следующий шаг, задавай уточняющие вопросы.\n"
        )

    # ---------- Internal helpers ----------

    def _build_messages(self, user_text: str) -> List[Dict[str, str]]:
        """
        Build messages for the LLM: system + (history) + current user message.

        Format — classic for chat.completions:
        [
          {"role": "system", "content": "..."},
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."},
          ...
        ]
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Use the tail of history to avoid huge context
        if self.history:
            trimmed = self.history[-2 * self.max_history_turns :]
            messages.extend(trimmed)

        messages.append({"role": "user", "content": user_text})
        return messages

    def _update_history(self, user_text: str, answer_text: str) -> None:
        """
        Append new user+assistant pair to history and trim to max_history_turns.
        """
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": answer_text})

        # Keep only the last max_history_turns pairs
        if len(self.history) > 2 * self.max_history_turns:
            self.history = self.history[-2 * self.max_history_turns :]

    # ---------- Public method used by alina_server.py ----------

    def handle_user_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        Main entry point for Alina.

        Input: raw audio bytes.
        Output: dict with transcript, answer, audio_base64, audio_mime, history.
        """

        # 1) STT — transcribe user audio
        user_text: str = stt_client.transcribe_audio(audio_bytes, filename)
        user_text = (user_text or "").strip()

        if not user_text:
            if self.mode == "en":
                user_text = "It seems the audio was empty or could not be recognized properly."
            else:
                user_text = "Похоже, звук был пустой или плохо распознан."

        # 2) LLM — get Alina's answer with dialogue memory
        messages = self._build_messages(user_text)

        answer_text: str = llm_client.chat_with_alina(messages)
        answer_text = (answer_text or "").strip()

        # 3) Update dialogue history
        self._update_history(user_text, answer_text)

        # 4) TTS — synthesize voice for Alina's answer
        audio_base64: str = tts_client.text_to_speech_base64(answer_text)

        result: Dict[str, Any] = {
            "transcript": user_text,
            "answer": answer_text,
            "audio_base64": audio_base64,
            "audio_mime": "audio/mpeg",
            "history": self.history,
        }
        return result
