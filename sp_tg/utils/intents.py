"""Всопогательный класс управлениея пользовательскими намерениями.

Прредоставляет специальный класс-обёртку для работы с пользовательскими
намерениями.
Позволяет добавлять, изменять и удалять намерения для каждого
пользователя.
"""

import sqlite3
from typing import NamedTuple, Optional

from sp.intents import Intent


class IntentObject(NamedTuple):
    """Описывает намерения пользователя.

    :param name: Имян намерения, которое также используется как ключ.
    :type name: str
    :param intent: Экземпляр пользовательского намерения.
    :type intent: Intent
    """

    name: str
    intent: Intent

class UserIntents:
    """Хранилище намерений пользователя.

    Является обёрткой над базой данных для хранения намерения.
    Содержит методы для добавления, имзенения парметров намерения
    и удаления намерений.

    :param conn: Подключение к базе данных где хранятся намерения.
    :type conn: sqlite3.Connection.
    :param uid: ID пользователя расписнаия.
    :type uid: str
    """

    def __init__(self, conn: sqlite3.Connection, uid: int) -> None:
        self._conn = conn
        self._cur = self._conn.cursor()
        self._uid = uid
        self._check_tables()

    def _check_tables(self) -> None:
        self._cur.execute(("CREATE TABLE IF NOT EXISTS intent("
            "user_id TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "intent TEXT NOT NULL)"
        ))
        self._conn.commit()

    # Работа со списком намерений ----------------------------------------------

    def get(self) -> list[IntentObject]:
        """Получает список всех намерений пользователя.

        :return: Список всхе намерений пользвоателя.
        :trype: list[IntentObject]
        """
        # Получаем имя и намерение из списка намерений для пользователя.
        self._cur.execute(
            "SELECT name,intent FROM intent WHERE user_id=?",
            (self._uid,)
        )
        return [IntentObject(n, Intent.from_str(i))
            for n, i in self._cur.fetchall()
        ]

    def get_intent(self, name: str) -> Optional[Intent]:
        """Возвращает первое намерение пользователя по имени.

        Возвращает первое подходящее по имени намерения.
        Если нету подходящего, то возаращет None.

        :param name: Имя намерения для поиска.
        :type name: str
        :return: Экземплыяр намерения или None, если нечего на найдено.
        :rtype: Optional[Intent]
        """
        self._cur.execute(
            "SELECT intent FROM intent WHERE user_id=? AND name=?",
            (self._uid, name)
        )
        res = self._cur.fetchone()
        if res is not None:
            return Intent.from_str(res[0])
        return

    def remove_all(self):
        """Удаляет все намерение пользователя из базы данных."""
        self._cur.execute("DELETE FROM intent WHERE user_id=?", (self._uid,))
        self._conn.commit()

    # Работа с одним намерением ------------------------------------------------

    def add(self, name: str, intent: Intent) -> None:
        """Добавляет намерение в базу данных.

        Добавляет запись в базу данных.
        Еслм такое намерение уже существует - обновляет.

        :param name: Имя намерения
        :type name: str
        :param intent: Экземпляр намерения для доабвления в базу данных.
        :type intent: Intent
        """
        int_s = intent.to_str()
        if self.get_intent(name) is not None:
            self._cur.execute(
                "UPDATE intent SET intent=? WHERE user_id=? AND name=?",
                (int_s, self._uid, name)
            )
        else:
            self._cur.execute(
                "INSERT INTO intent(user_id,name,intent) VALUES(?,?,?);",
                (self._uid, name, int_s)
            )
        self._conn.commit()

    def rename(self, old_name: str, new_name: str) -> None:
        """Изменяет имя намерения.

        Заменяет имя намерения в базе данных на новое.

        :param old_name: Старой имя намерения.
        :type old_name: str
        :param new_name: Новое имя для намерения.
        :type new_name: str
        """
        self._cur.execute(
            "UPDATE intent SET name=? WHERE user_id=? AND name=?",
            (new_name, self._uid, old_name)
        )
        self._conn.commit()

    def remove(self, name: str) -> None:
        """Удаляет намерение пользователя из базы данных.

        :param name: Имя намерения для удаления из базы данных.
        :typw name: str
        """
        self._cur.execute(
            "DELETE FROM intent WHERE user_id=? AND name=?",
            (self._uid, name)
        )
        self._conn.commit()
