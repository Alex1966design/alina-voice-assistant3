# alina_server.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from assistant.alina import AlinaAssistant

# ----------------------------------
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ FASTAPI
# ----------------------------------

app = FastAPI(
    title="Alina Voice Assistant",
    description="Отдельный сервер Алины: STT → LLM → TTS",
    version="1.0.0",
)

# CORS — чтобы можно было открывать из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ДВА экземпляра Алины с разными системными промптами и отдельной историей
assistant_ru = AlinaAssistant(mode="ru")
assistant_en = AlinaAssistant(mode="en")


# ----------------------------------
# HEALTHCHECK
# ----------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "alina"}


# ----------------------------------
# ГОЛОСОВОЙ ЭНДПОИНТ (RU / EN)
# ----------------------------------

@app.post("/alina/voice")
async def alina_voice(
        audio: UploadFile = File(...),
        lang: str = Form("ru"),  # "ru" или "en" приходит с фронта
):
    """
    Полный голосовой цикл Алины (RU/EN):

    1) STT → текст пользователя
    2) LLM → ответ Алины с учётом истории
    3) TTS → озвучка ответа (base64)

    Фронт отправляет multipart/form-data:
        audio=<файл>, lang="ru"|"en"
    """

    # читаем файл
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # выбираем нужный ассистент
    assistant = assistant_en if lang == "en" else assistant_ru

    try:
        result = assistant.handle_user_audio(
            audio_bytes,
            audio.filename or "audio.wav",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alina error: {e}")

    return result


# ----------------------------------
# ПРОСТОЙ ВЕБ-ИНТЕРФЕЙС ДЛЯ ДЕМО
# ----------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Простой HTML+JS интерфейс:
    - выбор языка (RU/EN)
    - запись с микрофона или выбор файла
    - отправка на /alina/voice
    """
    html = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Alina – голосовой ассистент</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f5f7;
      margin: 0;
      padding: 20px;
    }
    h1 {
      margin-bottom: 4px;
    }
    .subtitle {
      color: #777;
      margin-bottom: 20px;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.05);
      margin-bottom: 20px;
    }
    .btn {
      padding: 8px 16px;
      border-radius: 8px;
      border: 1px solid #ccc;
      cursor: pointer;
      background: #fff;
      font-size: 14px;
    }
    .btn-primary {
      background: #1a73e8;
      color: #fff;
      border-color: #1a73e8;
    }
    .btn-primary:disabled,
    .btn:disabled {
      opacity: 0.5;
      cursor: default;
    }
    .status-ok {
      color: #1a7f37;
      font-size: 14px;
      margin-left: 8px;
    }
    .status-error {
      color: #d93025;
      font-size: 14px;
      margin-left: 8px;
    }
    #reply-chat div.bubble {
      margin-bottom: 10px;
    }
    .bubble-header {
      font-size: 13px;
      color: #666;
      margin-bottom: 2px;
    }
    .bubble-user {
      display: inline-block;
      background: #e8f0fe;
      border-radius: 12px;
      padding: 8px 12px;
      max-width: 100%;
    }
    .bubble-alina {
      display: inline-block;
      background: #f1f3f4;
      border-radius: 12px;
      padding: 8px 12px;
      max-width: 100%;
    }
    pre {
      background: #f6f6f6;
      border-radius: 8px;
      padding: 10px;
      font-size: 12px;
      overflow-x: auto;
    }
  </style>
</head>
<body>
  <h1>Alina – голосовой ассистент</h1>
  <div class="subtitle">Отдельный сервер: STT → LLM → TTS (RU / EN)</div>

  <div class="card">
    <h3>Шаг 1. Запиши или выбери аудиофайл</h3>

    <div style="margin-bottom: 10px;">
      <input type="file" id="audio-file" accept="audio/*" />
      <span style="font-size: 12px; color:#777; margin-left:8px;">
        Можно выбрать готовый аудиофайл или записать голос с микрофона прямо в браузере.
      </span>
    </div>

    <div style="margin-bottom: 10px;">
      <button class="btn" id="btn-start">🎤 Начать запись</button>
      <button class="btn" id="btn-stop" disabled>⏹ Остановить запись</button>
      <span id="record-status" style="margin-left: 8px; font-size: 14px; color: #555;"></span>
    </div>

    <h3>Шаг 2. Отправь запрос Алине</h3>

    <div style="margin-bottom: 10px;">
      <label style="margin-right: 10px;">
        <input type="radio" name="lang" value="ru" checked />
        🇷🇺 Русский режим
      </label>
      <label>
        <input type="radio" name="lang" value="en" />
        🇬🇧 English mode
      </label>
    </div>

    <button class="btn btn-primary" id="btn-send">Отправить Алине</button>
    <span id="send-status"></span>
  </div>

  <div class="card">
    <h3>Ответ Алины</h3>
    <audio id="reply-audio" controls style="width: 100%; margin-bottom: 10px;"></audio>

    <div id="reply-chat" style="margin-bottom: 12px;"></div>

    <pre id="reply-history" style="display:none;"></pre>
  </div>

  <script>
    let mediaRecorder = null;
    let recordedChunks = [];

    const btnStart = document.getElementById("btn-start");
    const btnStop = document.getElementById("btn-stop");
    const recordStatus = document.getElementById("record-status");
    const btnSend = document.getElementById("btn-send");
    const sendStatus = document.getElementById("send-status");
    const audioFileInput = document.getElementById("audio-file");

    const replyAudio = document.getElementById("reply-audio");
    const replyChat = document.getElementById("reply-chat");
    const replyHistory = document.getElementById("reply-history");

    // ---------- Запись с микрофона ----------

    btnStart.onclick = async () => {
      recordedChunks = [];
      replyAudio.src = "";
      recordStatus.textContent = "";

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            recordedChunks.push(e.data);
          }
        };

        mediaRecorder.onstop = () => {
          recordStatus.textContent = "Запись завершена. Теперь можно отправить Алине.";
        };

        mediaRecorder.start();
        btnStart.disabled = true;
        btnStop.disabled = false;
        recordStatus.textContent = "Запись идёт…";
      } catch (err) {
        console.error(err);
        recordStatus.textContent = "Не удалось получить доступ к микрофону.";
      }
    };

    btnStop.onclick = () => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        btnStart.disabled = false;
        btnStop.disabled = true;
      }
    };

    // ---------- Отправка запроса Алине ----------

    btnSend.onclick = async () => {
      sendStatus.textContent = "";
      sendStatus.className = "";

      let audioBlob = null;
      let filename = "audio.wav";

      // 1) Приоритет — записанный голос
      if (recordedChunks.length > 0) {
        audioBlob = new Blob(recordedChunks, { type: "audio/webm" });
        filename = "recording.webm";
      } else {
        // 2) Если записи нет, пробуем взять файл
        const file = audioFileInput.files[0];
        if (!file) {
          alert("Сначала запишите голос или выберите аудиофайл.");
          return;
        }
        audioBlob = file;
        filename = file.name || "audio.wav";
      }

      const formData = new FormData();
      formData.append("audio", audioBlob, filename);

      const lang = document.querySelector('input[name="lang"]:checked').value;
      formData.append("lang", lang);

      btnSend.disabled = true;
      sendStatus.textContent = "Отправка…";
      sendStatus.className = "";

      try {
        const resp = await fetch("/alina/voice", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData.detail || ("HTTP " + resp.status));
        }

        const data = await resp.json();

        // Аудио
        if (data.audio_base64) {
          const mime = data.audio_mime || "audio/mpeg";
          replyAudio.src = `data:${mime};base64,${data.audio_base64}`;
          replyAudio.load();
        }

        // Пузырьки диалога
        replyChat.innerHTML = "";
        if (data.transcript) {
          const div = document.createElement("div");
          div.className = "bubble";
          div.innerHTML = `
            <div class="bubble-header">👤 Пользователь:</div>
            <div class="bubble-user">
              ${String(data.transcript).replace(/\\n/g, "<br>")}
            </div>
          `;
          replyChat.appendChild(div);
        }

        if (data.answer) {
          const div = document.createElement("div");
          div.className = "bubble";
          div.innerHTML = `
            <div class="bubble-header">🤖 Алина:</div>
            <div class="bubble-alina">
              ${String(data.answer).replace(/\\n/g, "<br>")}
            </div>
          `;
          replyChat.appendChild(div);
        }

        // История (при необходимости)
        replyHistory.style.display = "block";
        replyHistory.textContent =
          "История диалога (history):\\n" + JSON.stringify(data.history, null, 2);

        sendStatus.textContent = "Готово ✔";
        sendStatus.className = "status-ok";
      } catch (err) {
        console.error(err);
        sendStatus.textContent = "Ошибка ✖";
        sendStatus.className = "status-error";
      } finally {
        btnSend.disabled = false;
      }
    };
  </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


# ----------------------------------
# ЛОКАЛЬНЫЙ ЗАПУСК UVICORN
# ----------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "alina_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
