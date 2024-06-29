"""Хранилище пользователей.

.. note:: А как же SPMessages?

    ``SPMessages`` Лишилась методов для работы с пользователями.
    Поскольку задача класса представления - только предсоставлять
    расписание в удобном для платформы формате.

Позволяет управлять как базой данных пользователей,
так и каждым пользователей в отдельности.
Сами по себе храналищша не зависят от платформы, повышеая тем самым
переносимость на разные платформы.

.. caution:: Начальная фаза храналища

    Данное хранилища всё ещё находится на этапер аразработке.
    Формат данных пользоваеля всё ещё омжет изменяться.
    Однако большая часть API уде меняться не будет.
    Внимательно следите за выпусками обновлений.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional, Union

import ujson
from loguru import logger

from sp.intents import Intent
from sp.parser import Schedule
from sp.utils import compact_updates

# Вспомогательные контейнеры
# ==========================

class UserData(NamedTuple):
    """Данные пользователя внутри храналища.

    Данные пользователя привзываются к конкрутной платформе, а такке
    к своему поставщеку расписания.
    При смене платформы или поставщика расписания, хранилище
    пользователей также буедт изменено.

    Сами даныне предствлениы в формате только для чтения.
    Для изменения данных воспользуйтесь методами пользовательского
    хранилиша.

    :param create_time: Когда была создана учётная запись.
    :type create_time: Optional[int]
    :param cl: Класс пользователя по умолчанию.
    :type cl: Optional[str]
    :param set_class: Устанавливал ли пользователь класс.
    :type set_class: Optional[bool]
    :param last_parse: Временная метка последнего просмотренного
                       обновления в расписании
    :type last_parse: Optional[int]
    :param notifications: Включены ли уведомления у пользователя.
    :type notifications: Optional[bool]
    :param hours: В какие часы следует отправлять расписание
    :type hours: list[int]
    """

    create_time: Optional[int] = int(datetime.now().timestamp())
    cl: Optional[str] = None
    set_class: Optional[bool] = False
    last_parse: Optional[int] = 0
    notifications: Optional[bool] = True
    hours: list[int] = []


class CountedUsers(NamedTuple):
    """Результат подсчёта пользователей.

    Предоставляет статистические данные о хранилище пользователей.
    Сколькуо пользователей счиатются активными (временная метка
    последнего обновления совпадает с расписанием),
    а также какие классы заданы у пользователей.
    Используется в методе для подсчёта количества пользователей.

    active (int): Сколько пользователей использую обёртку.
    cl (Counter): Счётчик классов пользователей.
    """

    active: int
    cl: Counter


# Хранилище пользователей
# =======================

class FileUserStorage:
    """Хранилище пользователей в JSON файле.

    Используется чтобы взаимодействовать с пользователями платформ.
    Получать, добавлять, удалять, изменять данные пользователей.
    Содержит некоторые вспомогательные методы, к примеру подсчёт
    пользователям по классам.

    Является компонентом платформы.

    Также стоит обратить вниманеи что данные в хранилище сохраняются
    вручную.

    :param path: Путь к хранилищу пользователей.
    :type path: Path | str
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self._path = Path(path)
        self._users: Union[dict[str, UserData], None] = None


    # Функции для конвертации
    # =======================

    def _dict_to_userdata(self, user: dict) -> UserData:
        now = datetime.now().timestamp()
        return UserData(
            create_time=user.get("create_time", now),
            cl=user.get("cl", None),
            set_class=user.get("set_class", False),
            last_parse=user.get("last_parse", 0),
            notifications=user.get("notifications", False),
            hours=user.get("hours", [])
        )

    def _userdata_to_dict(self, user: UserData) -> dict:
        return {x[0]: x[1] for x in zip(user._fields, user)}


    # Работа с файлом хранилища
    # =========================

    def get_users(self) -> dict[str, UserData]:
        """Загружает данные всех пользователей.

        Подгружает даныне всех пользователей в словарь.
        Как ключ указывается id пользователя, как значение -
        ``UserData``.

        Тажке все полученные даныне кешируются, чтобы повысить
        скорость щагрузки.
        Если файла с пользователями нету, то возаращает пустой словарь.

        :return: Данные всех пользователей из храналища.
        :rtype: dict[str, UserData]
        """
        if self._users is None:
            try:
                with open(self._path) as f:
                    users = ujson.loads(f.read())
            except FileNotFoundError:
                users = {}
            self._users = {
                k: self._dict_to_userdata(v) for k, v in users.items()
            }
        return self._users

    def remove_users(self, user_ids: list[str]) -> None:
        """Удаляет сразу несколько пользователй из базы.

        Используется для прочистки списка пользователей.
        Напрмиер в сприпте проверки обновлений.
        Когда можно пользователей могут заблокировать бота или исключить
        его из чатов.
        Данный метод исключает всех пользователей, а после один раз
        сохраняет файл базы пользователй.

        :param user_ids: Список ID пользователей для удаления из базы.
        :type user_ids: list[str]
        """
        for uid in user_ids:
            try:
                self._users.pop(uid)
            except KeyError:
                logger.error("{} is not user", uid)
        self.save_users()

    def save_users(self) -> None:
        """Сохраняет данные пользователй в храналище.

        Переводит все даныне из словарява в понятный для храналища
        формат.
        Если файл не был создан, то создаёт его.
        После перезаписыват полностью данныее в файл.
        """
        users = {k: self._userdata_to_dict(v) for k, v in self._users.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            f.write(ujson.dumps(users))
        self._users = None

    def count_users(self, sc: Schedule) -> CountedUsers:
        """Подсчитывает пользователй хранилища.

        Вспомогательная статистическая функиця.
        Используется для сбора различной информации о пльзователях.
        К примеруц число пользователей, которые считаются активными.
        Также считает количество польователей по классам по умолчанию.

        :param sc: Относительно какого расписания производить подсчёт.
        :type: sc: Schedule
        :return: Статистическая информация о хранилище.
        :rtype: CountedUsers
        """
        if self._users is None:
            self.get_users()

        active_users = 0
        cl_counter = Counter()
        for k, v in self._users.items():
            cl_counter[v.cl] += 1
            if v.notifications and v.last_parse >= sc.schedule["last_parse"]:
                active_users += 1
        return CountedUsers(active_users, cl_counter)


    # Рабоат с пользователями базы
    # ============================

    def create_user(self, uid: str) -> None:
        """Создает нового пользователя.

        Вы можете использовать этот метод как для создания, так и для
        сброса данных пользователя к значениям по умолчанию.
        Все новые пользователя создаются со стандратными значениями
        ``UserData``.

        :param uid: Уникальный ID пользователя.
        :type uid: str
        """
        if self._users is None:
            self.get_users()
        self._users[uid] = UserData()

    def get_user(self, uid: str) -> UserData:
        """Получает данные пользователя по его UID.

        Получшеныне данные используются только для чтения.
        Для зменения данныех нужно использовать или методы хранилиша,
        или вспомогательный класс User.

        :param uid: Уникальный ID пользователя.
        :type uid: str
        :return: Данные пользователя из хранилища.
        """
        if self._users is None:
            self.get_users()

        return self._users.get(uid, UserData())

    def remove_user(self, uid: str) -> None:
        """Удаляет пользователя из храналища по его UID.

        Если вы попытаетесь удалить не существующего пользователя,
        то вам выдаст исключение.

        :param uid: Уникальный ID пользовтеля для удаления из хранилища.
        :type uid: str
        """
        if self._users is None:
            self.get_users()

        self._users.pop(uid, None)

    def set_class(self, uid: str, cl: Optional[str], sc: Schedule) -> bool:
        """Устанавливает класс по умолчанию пользователю.

        Для начала вам нужно передать относительно какого расписнаия
        устанавливается класс.
        Вы можеет передать как строку, так и None.
        Последнее, чтобы явно отвзяать пользователя от класса.
        Если такого класса нет в расписнаии, вам вернётся False.
        Иначе же произойдёт следующее.

        - Класс будет установлен на заданный.
        - Флаг утсановки класса станет положительным.
        - Время последней проверки соотнесётся с проверкой расписнаия.

        :param uid: Для какого пользователя из базы установить класс.
        :type uid: str
        :param cl: Какой класс установить пользователю.
        :type cl: Optional[str]
        :param sc: Относительно какого расписания установить класс.
        :type sc: Schedule
        :return: Стутус смены класса. True - класс был изменён.
        :rtype: bool
        """
        user = self.get_user(uid)
        if cl is None or cl in sc.lessons:
            self._users[uid] = UserData(
                create_time=user.create_time,
                cl=cl,
                set_class=True,
                last_parse=sc.schedule["last_parse"],
                notifications=user.notifications,
                hours=user.hours
            )
            return True
        else:
            return False

    def unset_class(self, uid: str) -> None:
        """переводит пользователя в режим выбора класса.

        В отличе от полного сброса пользователя, некоторые параметры
        остаются неизменными.
        Потому предпочтительнее именно не сбрасывать, а снимать
        флаг выбора класса этим методом.

        - Снимает флаг выбора класса пользователя.
        - Сбрасывает класс по умолчанию.
        - Не трогает все остальные параментры пользовтеля.

        :param uid: Для какого пользователя нужно снять класс.
        :type uid: str
        """
        user = self.get_user(uid)
        self._users[uid] = UserData(
            create_time=user.create_time,
            cl=None,
            set_class=False,
            last_parse=user.last_parse,
            notifications=user.notifications,
            hours=user.hours
        )

    def update_user(self, uid: str, user: UserData) -> None:
        """Обновляет данные пользователя.

        в отличие от остальных методов, этот метод позволяет напрямую
        перезаписывать данные пользователя.
        Потому будьте осторожны с ним, если не хотите всё сломать.
        Также этот метод не делает никаких проверок на существования
        пользователя, так что им тоже вполне можно создавать
        новых пользователей уже с азаданными настройками.
        Например чтобы делать дубликаты пользователей или маграции.

        :param uid: ID пользователя в хранилище.
        :type uid: str
        :param user: Новые данные пользователя для перезаписи.
        :type user: UserData
        """
        if self._users is None:
            self.get_users()

        self._users[uid] = user


class User:
    """Вспомогательный класс работы с пользваотелем храналащи.

    Передвая хранилища и ID пользователя для более удобной работы
    с хранилищем пользователя.

    :param storage: Хранилише пользователя.
    :type storage: FileUserStorage
    :param uid: ID пользователь для работы с хранилищем.
    :type uid: str
    """

    def __init__(self, storage: FileUserStorage, uid: str) -> None:
        self.uid = uid
        self._storage = storage
        self.data = self._storage.get_user(uid)

    def create(self) -> None:
        """Создает нового пользователя.

        Также как и схранилищем пользователя может как создать
        пользователя, так и перезаписать данные до значений по
        умолчанию.
        После создания пользователя сохраняет данные хранилища.
        """
        self._storage.create_user(self.uid)
        self._storage.save_users()
        self.data = self._storage.get_user(self.uid)

    def remove(self) -> None:
        """Удаляет данные пользователя.

        В отличе от метода хранилища, которое напрямую удаляет данные
        пользователя, данный метод не удалит пользователя, если он
        не существует.
        """
        if self.data is not None:
            self._storage.remove_user(self.uid)
            self._storage.save_users()
            self.data = UserData()

    def set_class(self, cl: str, sc: Schedule) -> bool:
        """Устанавливает класс пользователя.

        Если класс будет установлен, то сохраняет данные хранилища.
        Также как и с методов хранилищаЮ, возвращает стасус смены
        класса.

        - Класс будет установлен на заданный.
        - Флаг утсановки класса станет положительным.
        - Время последней проверки соотнесётся с проверкой расписнаия.

        :param cl: Какой класс необходимо устновить.
        :type cl: str
        :param sc: Относительно какого расписнаия изменять класс.
        :return: Стутс смены класса. True - класс изменён.
        """
        res = self._storage.set_class(self.uid, cl, sc)
        if res:
            self._storage.save_users()
            self.update()
        return res

    def unset_class(self) -> None:
        """Снимает выбор класса пользователя.

        В отличие от простого сброса данных пользователя по умолчанию,
        данный метод только переводит класс в None, а флаг что класс
        был установлен в False.
        Это нужно чтобы прочие настройки пользоваеля были не тронуты.
        """
        self._storage.unset_class(self.uid)
        self._storage.save_users()
        self.update()

    def save(self, save_users: Optional[bool]=True) -> None:
        """Сохраняет текушие локальные данные пользователя.

        .. deprecated:: 6.0

            Данные метод может быть в любое время удалёен.
            Поскольку логично его не должно быть.
        """
        self._storage.update_user(self.uid, self.data)
        if save_users:
            self._storage.save_users()

    def update(self) -> None:
        """Перезаписывает локальные данные, данными из хранилища."""
        self.data = self._storage.get_user(self.uid)

    def get_updates(self, sc: Schedule, save_users: Optional[bool]=True
    ) -> Optional[dict[str, Union[str, dict]]]:
        """Возаращает все не просмотренные записи об изменениях.

        Полчает все новые записи об изменниях в расписании, начиная
        с текущей отметки ``last_parse`` пользователя.
        Все записи об изменениях сживаются при помощи
        :py:func:`sp.sp.utils.compact_updates`.
        После получения всех имзенений, метка последней проверки
        сдвигается до времени последней записи об изменениях.

        .. note:: Хранилище изменений

            В скором времени этот метоб будет перенесён в хранилище
            списка изменений.

        :param sc: Относительно какогор расписания получать изменения.
        :type sc: Schedule
        :param save_users: Обноявлять ли временную метку обновления.
        :type save_users: Optional[bool]
        :return: Сжайтый список изменений расписания пользователя.
        :rtype: Optional[dict[str, Union[str, dict]]]
        """
        if self.data.cl is None:
            return

        if sc.schedule["last_parse"] <= self.data.last_parse:
            return

        logger.info("Get lessons updates")
        i = Intent.construct(sc, cl=[self.data.cl])
        updates = sc.get_updates(i, self.data.last_parse)

        # Обновление времени последней проверки расписания
        new_user = UserData(
                create_time=self.data.create_time,
                cl=self.data.cl,
                set_class=self.data.set_class,
                last_parse=sc.schedule["last_parse"],
                notifications=self.data.notifications,
                hours=self.data.hours
        )
        self.save(new_user, save_users)

        if save_users:
            self._storage.save_users()

        if len(updates) != 0:
            return compact_updates(updates)
        else:
            return

    # Настройки уведомлений
    # =====================

    def set_notify_on(self) -> None:
        """Включает уведомления пользователя."""
        self.data = UserData(
                create_time=self.data.create_time,
                cl=self.data.cl,
                set_class=self.data.set_class,
                last_parse=self.data.last_parse,
                notifications=True,
                hours=self.data.hours
        )
        self.save()

    def set_notify_off(self) -> None:
        """Выключает уведомления пользователя."""
        self.data = UserData(
                create_time=self.data.create_time,
                cl=self.data.cl,
                set_class=self.data.set_class,
                last_parse=self.data.last_parse,
                notifications=False,
                hours=self.data.hours
        )
        self.save()

    def add_notify_hour(self, hour: int) -> None:
        """Добавляет рассылку в укзаанный час.

        Обратите вниманеи что на данынй момент не происходит
        валидация числовых значений, так что самостоятельно убедитесь
        что вы передаёте час от 6-ти утра и 20-ти вечера.

        :param hour: _description_
        :type hour: int
        """
        if hour not in self.data.hours:
            self.data.hours.append(hour)
            self.save()

    def remove_notify_hour(self, hour: int) -> None:
        """Удаляет рассылку расписнаия в указанное время.

        Обратите вниманеи что на данынй момент не происходит
        валидация числовых значений.
        Если вы попытаетесь выключить уведомления для того времени,
        которое ранее не было установлено, то полчите исключение.

        :param hour: Час, для которого отключить уведомления.
        :type hour: int
        """
        if hour in self.data.hours:
            self.data.hours.remove(hour)
            self.save()

    def reset_notify(self) -> None:
        """Сбрасывает часы рассылка расписания расписания."""
        self.data = UserData(
                create_time=self.data.create_time,
                cl=self.data.cl,
                set_class=self.data.set_class,
                last_parse=self.data.last_parse,
                notifications=self.data.notifications,
                hours=[]
        )
        self.save()
