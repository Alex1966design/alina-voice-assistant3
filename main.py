# main.py — тонкий адаптер для Railway

import os
from alina_server import app  # FastAPI-приложение из alina_server.py


# Экспортируем app, чтобы можно было запускать uvicorn main:app
# при желании (например, локально через CLI).
# app уже импортирован строкой выше.


if __name__ == "__main__":
    # Локальный / Railway-запуск через "python main.py"
    import uvicorn

    uvicorn.run(
        app,  # передаём сам объект приложения, а не строку
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=False,
    )
