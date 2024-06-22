"""Представляет класс для хранения намерений платформы.

Используется для сохранения пользовательских намерений.
Пользовательские намерения будут заменой классу по умолчанию.
Пользователь для быстрого доступа сможет сохранять свои намерения.

Это хранилище предоставляет классы для упрвления пользовательскими
намерениями.
Добавленя, изменения и удаления отдельно для каждого пользователя
внутри конкретной платформы.
"""

import sqlite3
from typing import NamedTuple, Optional

from sp.intents import Intent


# Вспомогательные классы
# ======================

class IntentObject(NamedTuple):
    """Описывает одно намерение пользователя в хранилище.

    :param name: Имя намерения, используется как ключ.
    :type name: str
    :param intent: Экземпляр пользовательского намерения.
    :type intent: Intent
    """

    name: str
    intent: Intent


# Основной класс хранилища
# ========================

class UserIntentsStorage:
    """Хранилище намерений пользователя для платформы.

    Является обёрткой над базой данных для хранения намерения.
    Содержит методы для добавления, изменения парметров намерения
    и удаления намерений.

    :param path: Путь к базе данных хранилища.
    :type path: str
    :param uid: ID пользователя расписнаия.
    :type uid: str
    """

    def __init__(self, path: str, uid: int) -> None:
        self.path = path
        self.uid = uid
        self._db = sqlite3.connect(path)
        self._check_tables()

    def _check_tables(self) -> None:
        self._db.execute(("CREATE TABLE IF NOT EXISTS intent("
            "user_id TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "intent TEXT NOT NULL)"
        ))
        self._db.commit()

    # Работа со списком намерений ----------------------------------------------

    def get(self) -> list[IntentObject]:
        """Получает список всех намерений пользователя.

        Возвращает готовый к работе список намерений пользователя.

        :return: Список всех намерений пользвоателя.
        :trype: list[IntentObject]
        """
        # Получаем имя и намерение из списка намерений для пользователя.
        cur = self._db.cursor()
        cur.execute(
            "SELECT name,intent FROM intent WHERE user_id=?",
            (self.uid,)
        )
        return [IntentObject(n, Intent.from_str(i))
            for n, i in cur.fetchall()
        ]

    def get_intent(self, name: str) -> Optional[Intent]:
        """Возвращает первое намерение пользователя по имени.

        Возвращает первое подходящее по имени намерения.
        Если нету подходящего, то возаращет None.

        Используется если нужно получить какое-то конкретное намерение
        из общего хранилища по его имени.

        :param name: Имя намерения для поиска.
        :type name: str
        :return: Экземплыяр намерения или None, если нечего на найдено.
        :rtype: Optional[Intent]
        """
        cur = self._db.cursor()
        cur.execute(
            "SELECT intent FROM intent WHERE user_id=? AND name=?",
            (self.uid, name)
        )
        res = cur.fetchone()
        if res is not None:
            return Intent.from_str(res[0])
        return

    def remove_all(self):
        """Удаляет все намерение пользователя из базы данных."""
        self._db.execute("DELETE FROM intent WHERE user_id=?", (self.uid,))
        self._db.commit()

    # Работа с одним намерением ------------------------------------------------

    def add(self, name: str, intent: Intent) -> None:
        """Добавляет намерение в базу данных.

        Вы можете использовать этот метод как для создания нового
        намерениея, так и для изменения старого.
        Если такое намерение уже существует, то будет перезаписано.

        :param name: Имя намерения для добавления/изменения.
        :type name: str
        :param intent: Экземпляр намерения для доабвления в базу данных.
        :type intent: Intent
        """
        int_s = intent.to_str()
        cur = self._db.cursor()
        if self.get_intent(name) is not None:
            cur.execute(
                "UPDATE intent SET intent=? WHERE user_id=? AND name=?",
                (int_s, self.uid, name)
            )
        else:
            cur.execute(
                "INSERT INTO intent(user_id,name,intent) VALUES(?,?,?);",
                (self.uid, name, int_s)
            )
        self._db.commit()

    def rename(self, old_name: str, new_name: str) -> None:
        """Изменяет имя намерения.

        В отличие от метода `add`, меняем имя намерения на новое.
        При этом не затрагивая содержимое самого намерения.
        Обратите внимание, не происходит никаких проверок.
        Если такого немерения не существует, ничего не произойдёт.
        Статусных кодов возврата также не предусмотрено.

        :param old_name: Старой имя намерения.
        :type old_name: str
        :param new_name: Новое имя для намерения.
        :type new_name: str
        """
        self._db.execute(
            "UPDATE intent SET name=? WHERE user_id=? AND name=?",
            (new_name, self.uid, old_name)
        )
        self._db.commit()

    def remove(self, name: str) -> None:
        """Удаляет намерение пользователя из базы данных.

        Удаляет намерение из базы данных по его имени.
        Обратиет внимание что у этого метода не проверок.
        Если вы укажете не существующие имя, то ничего не произойдёт.

        :param name: Имя намерения для удаления из базы данных.
        :typw name: str
        """
        self._db.execute(
            "DELETE FROM intent WHERE user_id=? AND name=?",
            (self.uid, name)
        )
        self._db.commit()
