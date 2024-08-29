"""Представляет класс для хранения намерений платформы.

Пользовательские намерения будут заменой классу по умолчанию.

Пользовательскиое намерение представляет собой именованное намерение.
Ползователь может создавать несколько намерений. присваивая им имена,
чтобы после получить к ним доступ, используя для этого ранее заданные
имена.

Также пользователь после может изменять намерения, задавть им новые
имена или полностью удалять.
"""

import sqlite3
from typing import NamedTuple, Iterator

from loguru import logger

from sp.intents import Intent

# Имя намерения по умолчанию
# Данное имя будет использовать, когда нужно будет провести
# операции с намерением пользователя по умолчанию
DEFAULT_INTENT_NAME = "main"

# Вспомогательные классы
# ======================

class IntentObject(NamedTuple):
    """Описывает одно намерение пользователя в хранилище.

    Каждое намерение в хранилище хранистя в формате ключ - значение.
    Это позвоялет легко получат намерения по их названию.
    Также по данному ключу может и не быть намерения, или его
    невозможно будет прочитать.

    :param name: Имя намерения, используется как ключ.
    :type name: str
    :param intent: Экземпляр пользовательского намерения.
    :type intent: Intent | None
    """

    name: str
    intent: Intent | None


# Основной класс хранилища
# ========================

class UserIntentsStorage:
    """Хранилище пользовательских намерений для платформы.

    Пользовательские намерения представляют собой именованные намренеия,
    котрые пользователя могут создавать для более быстрого доступа к
    часто используемым намерениям.

    Данное хранилище предосталвяет возможность для созданрия новых
    намерений, а также их последующего просмотра и изменения.
    Хранилище построено на базе данных Sqlite, что вероятно не самый
    оптимальный выбор, учитывая что данные хранятся в формате
    ключ - значение.

    :param path: Путь к файлу базы данных для конкретной платформы.
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


    # Получение намреений
    # ===================

    def __len__(self) -> int:
        """Получает количество намерений пользовтеля."""
        cur = self._db.cursor()
        cur.execute(
            "SELECT name,intent FROM intent WHERE user_id=?",
            (self.uid,)
        )
        return len(cur.fetchall())

    def __iter__(self) -> Iterator[IntentObject]:
        """Позвоялет по очереди получать каждое намерение пользователя.

        :return: Экземпляр намерения из базы данных.
        :rtype: IntentObject
        """
        return self.get()

    def _get_intent_object(self, name: str, intent_str: str) -> IntentObject:
        try:
            intent = Intent.from_str(intent_str)
        except Exception as e:
            logger.error(
                "Error while unpack intent {} ({}): {}",
                name, intent_str, e
            )
            intent = Intent()

        return IntentObject(name, intent)

    def get(self) -> Iterator[IntentObject]:
        """Получает список всех намерений пользователя.

        Намерения возвращаеются в виде списка IntentObject.

        :yield: Экземпляр намерения пользователя.
        :trype: list[IntentObject]
        """
        # Получаем имя и намерение из списка намерений для пользователя.
        cur = self._db.cursor()
        cur.execute(
            "SELECT name,intent FROM intent WHERE user_id=?",
            (self.uid,)
        )
        for n, i in cur:
            yield self._get_intent_object(n, i)

    def get_intent(self, name: str) -> Intent | None:
        """Возвращает первое намерение пользователя по имени.

        Используется если нужно получить какое-то конкретное намерение
        из общего хранилища по его имени.
        Если етьс несколько намерений с одинаковым именем - вернёт
        первое.
        Если намерений с таким именем нет, то вернёт None.

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
            try:
                return Intent.from_str(res[0])
            except Exception as e:
                logger.error("Error load intent {} ({}): {}", name, res[0], e)
                return Intent()
        return

    def remove_all(self):
        """Удаляет все намерение пользователя из базы данных."""
        self._db.execute("DELETE FROM intent WHERE user_id=?", (self.uid,))
        self._db.commit()


    # Управление конкретным намерением
    # ================================

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

        В отличие от метода ``add()``, меняет имя намерения на новое.
        При этом не затрагивая содержимое самого намерения.
        Обратите внимание, не происходит никаких проверок.
        Если такого немерения не существует - ничего не произойдёт.
        Статусных кодов возврата также не предусмотрено.

        :param old_name: Старое имя намерения.
        :type old_name: str
        :param new_name: Новое имя намерения.
        :type new_name: str
        """
        self._db.execute(
            "UPDATE intent SET name=? WHERE user_id=? AND name=?",
            (new_name, self.uid, old_name)
        )
        self._db.commit()

    def remove(self, name: str) -> None:
        """Удаляет намерение из базы данных по его имени.

        Обратите внимание что у этого метода нет проверок.
        Если вы укажете не существующее имя, то ничего не произойдёт.
        Статусных кодов также не предусмотрено.

        :param name: Имя намерения для удаления из базы данных.
        :typw name: str
        """
        self._db.execute(
            "DELETE FROM intent WHERE user_id=? AND name=?",
            (self.uid, name)
        )
        self._db.commit()


    # Намерение по умолчанию
    # ======================

    def default(self) -> Intent:
        """Полчает намерение по умолчанию или пустое намерение.

        Намерение по умолчанию представляет собой именованное намерение
        в хранилище с имененм ``main``.
        Используется когда нам нужно передавать в классы представления
        некоотрое намренеие, однако нам его не передали.
        Тогда в ход вступает намеренеи по умолчанию.

        :return: Намерение по умолчанию или пустое намерение намерение.
        :rtype: Intent
        """
        intent = self.get_intent(name=DEFAULT_INTENT_NAME)
        return intent if intent is not None else Intent()

    def get_default(self) -> Intent | None:
        """Получает намеренеи по умолчанию.

        В отличие от прошлого метода где мы получаем намерение,
        даже если его не существует, здесь мы получим None, если у
        пользовтеля не существует намерения по умолчанию.
        Это будет полезно в тех случаях, когда мы хотим узнать,
        устанавливал пользователь намерение по умолчанию или нет.
        В некотором роде для обратной совместимости.

        :return: Намерение пользователя по умолчанию.
        :rtype: Optional[Intent]
        """
        return self.get_intent(name=DEFAULT_INTENT_NAME)

    def set_default(self, intent: Intent) -> None:
        """Устанавливает намерение по умолчанию.

        Подобно тому как мы задавали класс пользователю, данным
        методом мы задаём намерение пользователя по умолчнанию.
        Оно будет использовать для автоматической подстановки в методы
        класса представления.

        :param intent: Устанавливаемое намерение по умолчанию.
        :type intent: Intent
        """
        self.add(name=DEFAULT_INTENT_NAME, intent=intent)
