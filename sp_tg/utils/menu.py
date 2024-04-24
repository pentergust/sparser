from typing import NamedTuple, Optional
from pathlib import Path

from sp.utils import load_file, save_file

from icecream import ic

import aiosqlite


dp_conn = aiosqlite.connect("buttons.db")


class Button(NamedTuple):
    id: int
    name: str
    callback: str
    class_requre: bool
    pinned: bool


BOT_BUTTONS = [
    Button(0, "Уроки", "sc:{cl}:today", True, True),
    Button(1, "Намерения", "intents", False, True)
]


class UserButtons:
    def __init__(self, conn: aiosqlite.Connection, uid: str):
        self._conn: aiosqlite.Connection = conn
        self.uid = uid

    async def _create_tables(self) -> None:
        cur = await self._conn.cursor()
        await cur.execute((
            "CREATE TABLE IF NOT EXISTS menu_buttons("
            "id INTEGER NOT NULL,"
            "user_id INTEGER NOT NULL,"
            "name TEXT NOT NULL,"
            "pinned INTEGER NOT NULL,"
            "class_require INTEGER NOT NULL,"
            "callback_data TEXT NOT NULL,"
            "PRIMARY KEY('id' AUTOINCREMENT));"
        ))
        await self._conn.commit()

    async def get_all(self):
        cur = await self._conn.cursor()
        await cur.execute(
            "SELECT * FROM menu_button WHERE user_id=?",
            (self.uid)
        )
        # for x in cur. 


# class ButtonMenu:
#     def __init__(self, buttons: list[Button], cl: Optional[str]=None):
#         self._buttons = buttons

#     def get_pinned(self) -> list[Button]:
#         return [b for b in self._buttons if b.pinned]

#     def get_other(self) -> list[Button]:
#         return [b for b in self._buttons if b.pinned == False]

#     def get_by_id(self, Button_id: int):
#         for x in self._buttons:
#             if x.id == Button_id:
#                 return x
#         return None

# class UserButtons(ButtonMenu):

#     def __init__(self, uid: str, users_file: Optional[Path]=DEFAULT_USER_PATH):
#         self.uid = uid
#         self.user_file = users_file
#         self.buttons = self._load_user_buttons()
#         super().__init__(self, self.buttons)


#     def _load_user_buttons(self) -> list[Button]:
#         ubuttons = load_file(self.user_file).get(self.uid)
#         return ubuttons if ubuttons is not None else BOT_BUTTONS.copy()
