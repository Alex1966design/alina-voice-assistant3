# main.py — тонкий адаптер для Railway

import os

from alina_server import app  # импортируем FastAPI-приложение из alina_server.py


# Если кто-то запустит "uvicorn main:app", нужно, чтобы app был доступен в этом модуле
# Поэтому просто экспортируем app, без дополнительной логики.


if __name__ == "__main__":
    # Локальный запуск, если вдруг запустить "python main.py"
    import uvicorn

    uvicorn.run(
        "main:app",                      # этот модуль (main), атрибут app
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=False,
    )
