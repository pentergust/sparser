"""Простой backend web сервер, написанный на FastAPI.

Позволяет получить JSON расписание уроков от парсера.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sp.parser import Schedule

# Временно будем хранить тут нашу версию
_SERVER_VERSION = "v0.1"
app = FastAPI()

# Вместо плдключения платформы мы напрямую будем использовать расписание
# Поскольку класс расписания отдаёт нам "сырой" результат
# Который мы будем получать уже на стороне фронтенда
# Успех!
sc = Schedule()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get_root() -> dict[str, str | bool]:
    """Если кто-то постучится к нам на сервер.

    Вернём ему что всё хорошо и вот версия нашего сервера.
    Хотя конечно, вряд-ли кто-то будет стучаться напрямую.
    Хотя... может быть.
    """
    return {"ok": True, "version": _SERVER_VERSION}

@app.get("/sc")
async def get_sc() -> dict:
    """Запрос на получение расписания.

    Пока что будет отдавать полное расписание.
    Хотя конечно лучше было бы организовать это несколько иначе.
    """
    return sc.lessons
