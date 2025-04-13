"""Хранилище пользователей.

Позволяет управлять базой данных пользователей и каждым пользователем отдельно.
Сами по себе хранилища не зависят от платформы, повышая тем самым
переносимость на разные платформы.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import ujson
from loguru import logger

from sp.intents import Intent
from sp.parser import Schedule
from sp.updates import compact_updates

# Вспомогательные контейнеры
# ==========================


class UserData(NamedTuple):
    """Данные пользователя внутри хранилища.

    Данные пользователя привязывается к конкретной платформе, а также
    к своему поставщику расписания.
    При смене платформы или поставщика расписания, хранилище
    пользователей также будет другим.

    Сами данные представлены в формате только для чтения.
    Для изменения данных воспользуйтесь методами пользовательского
    хранилища.

    :param create_time: Когда была создана учётная запись.
    :param cl: Класс пользователя по умолчанию.
    :param set_class: Устанавливал ли пользователь класс.
    :param last_parse: Временная метка последнего просмотренного
                       обновления в расписании
    :param notifications: Включены ли уведомления у пользователя.
    :param hours: В какие часы следует отправлять расписание
    """

    create_time: int | None = int(datetime.now().timestamp())
    cl: str | None = None
    set_class: bool | None = False
    last_parse: int = 0
    notifications: bool | None = True
    hours: list[int] = []


class CountedUsers(NamedTuple):
    """Результат подсчёта пользователей.

    Предоставляет статистические данные о хранилище пользователей.
    Сколько пользователей считаются активными (временная метка
    последнего обновления совпадает с расписанием),
    а также какие классы заданы у пользователей.
    Используется в методе для подсчёта количества пользователей.

    total (int): Сколько всего пользователей платформы.
    notify (int): Сколько пользователей включили уведомления.
    active (int): Сколько пользователей использую платформу.
    cl (Counter): Счётчик классов пользователей.
    hours (Counter): счётчик времени отправки расписания.
    """

    total: int
    notify: int
    active: int
    cl: Counter
    hour: Counter


# Хранилище пользователей
# =======================


class FileUserStorage:
    """Хранилище пользователей в JSON файле.

    Используется чтобы взаимодействовать с пользователями платформы.
    Получать, добавлять, удалять, изменять данные пользователей.
    Содержит некоторые вспомогательные методы, к примеру статистика
    пользователей хранилища.

    Также стоит обратить внимание что данные в хранилище сохраняются
    вручную.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._users: dict[str, UserData] = {}

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
            hours=user.get("hours", []),
        )

    def _userdata_to_dict(self, user: UserData) -> dict:
        return {x[0]: x[1] for x in zip(user._fields, user)}

    # Работа с файлом хранилища
    # =========================

    def get_users(self) -> dict[str, UserData]:
        """Загружает данные всех пользователей.

        Подгружает данные всех пользователей в словарь.
        Как ключ указывается id пользователя, как значение -
        ``UserData``.

        Также все полученные данные кешируются, чтобы повысить
        скорость загрузки.
        Если файла с пользователями нет, то вернёт пустой словарь.
        """
        if self._users is None:
            try:
                self._path.parent.mkdir(exist_ok=True, parents=True)
                with open(self._path) as f:
                    users = ujson.loads(f.read())
            except FileNotFoundError:
                users = {}
            self._users = {
                k: self._dict_to_userdata(v) for k, v in users.items()
            }
        return self._users

    def remove_users(self, user_ids: list[str]) -> None:
        """Удаляет сразу несколько пользователей из базы.

        Используется для прочистки списка пользователей.
        Например в скрипте автоматической проверки обновлений.
        Данный метод исключает всех пользователей, а после один раз
        сохраняет файл базы пользователей.
        """
        for uid in user_ids:
            try:
                self._users.pop(uid)
            except KeyError:
                logger.error("{} is not user", uid)
        self.save_users()

    def save_users(self) -> None:
        """Сохраняет данные пользователей в хранилище.

        Если файл не был создан, то создаёт его.
        После перезаписывает полностью данные в файл.
        """
        users = {k: self._userdata_to_dict(v) for k, v in self._users.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            f.write(ujson.dumps(users))

    def count_users(self, sc: Schedule) -> CountedUsers:
        """Подсчитывает пользователей хранилища.

        Вспомогательная статистическая функция.
        Используется для сбора различной информации о пользователях.
        К примеру число пользователей, которые считаются активными.
        Также считает количество пользователей по классам.
        """
        if self._users is None:
            self.get_users()

        total_users = len(self._users)
        notify_users = 0
        active_users = 0
        cl_counter: Counter[str] = Counter()
        hour_counter: Counter[int] = Counter()
        for k, v in self._users.items():
            cl_counter[str(v.cl)] += 1
            if v.notifications:
                notify_users += 1

                for hour in v.hours:
                    hour_counter[hour] += 1

                if v.last_parse >= sc.schedule["last_parse"]:
                    active_users += 1

        return CountedUsers(
            total_users, notify_users, active_users, cl_counter, hour_counter
        )

    # Работа с пользователями базы
    # ============================

    def create_user(self, uid: str) -> None:
        """Создает нового пользователя.

        Вы можете использовать этот метод как для создания, так и для
        сброса данных пользователя к значениям по умолчанию.
        Все новые пользователя создаются со стандартными значениями
        ``UserData``.
        """
        if self._users is None:
            self.get_users()
        self._users[uid] = UserData()

    def get_user(self, uid: str) -> UserData:
        """Получает данные пользователя по его ID.

        Полученные данные можно только для чтения.
        Для изменения данных пользователя воспользуйтесь
        предоставленными методами хранилища,
        или вспомогательный класс User.
        Если такого пользователя нет, то вернёт данные по умолчанию.
        """
        if self._users is None:
            self.get_users()

        return self._users.get(uid, UserData())

    def remove_user(self, uid: str) -> None:
        """Удаляет пользователя из хранилища по его UID.

        Если вы попытаетесь удалить не существующего пользователя,
        то вам выдаст исключение.
        """
        if self._users is None:
            self.get_users()

        self._users.pop(uid, None)

    def set_class(self, uid: str, cl: str | None, sc: Schedule) -> bool:
        """Устанавливает класс пользователя по умолчанию.

        .. note:: У нас есть намерения по умолчанию.

            Как только намерения по умолчанию станут основным способом
            использовать расписание, то классы по умолчанию благополучно
            исчезнут вместе с методами хранилища.

        Для начала вам нужно передать относительно какого расписания
        устанавливается класс.
        Вы можете передать как строку или None.
        None используется чтобы явно отвязать пользователя от класса.
        Если такого класса нет в расписании, функция вернёт False.
        Иначе же произойдёт следующее.

        - Класс будет установлен на заданный.
        - Флаг установленного класса станет True.
        - Время последней проверки сравняется с временем расписания.
        """
        user = self.get_user(uid)
        if cl is None or cl in sc.lessons:
            self._users[uid] = UserData(
                create_time=user.create_time,
                cl=cl,
                set_class=True,
                last_parse=sc.schedule["last_parse"],
                notifications=user.notifications,
                hours=user.hours,
            )
            return True
        return False

    def unset_class(self, uid: str) -> None:
        """Переводит пользователя в режим выбора класса.

        В отличие от полного сброса пользователя, некоторые параметры
        остаются не тронутыми.
        Потому предпочтительнее именно не сбрасывать данные, а снимать
        флаг выбора класса этим методом.

        - Снимает флаг выбора класса пользователя.
        - Сбрасывает класс по умолчанию.
        - Не трогает все остальные параметры пользователя.
        """
        user = self.get_user(uid)
        self._users[uid] = UserData(
            create_time=user.create_time,
            cl=None,
            set_class=False,
            last_parse=user.last_parse,
            notifications=user.notifications,
            hours=user.hours,
        )

    def update_user(self, uid: str, user: UserData) -> None:
        """Обновляет данные пользователя.

        в отличие от остальных методов, этот метод позволяет напрямую
        перезаписывать данные пользователя.
        Потому будьте осторожны с ним, если не хотите всё сломать.
        Также этот метод не делает никаких проверок на существование
        пользователя, так что им тоже вполне можно создавать
        новых пользователей уже с заданными настройками.
        Например чтобы делать дубликаты пользователей.

        Не забудьте после вручную сохранить хранилище.
        """
        if self._users is None:
            self.get_users()

        self._users[uid] = user


class User:
    """Вспомогательный класс работы с пользователем хранилища.

    Позволяет более удобно управлять конкретным пользователем.
    Именно этот класс чаще всего будет использовать в платформе.
    Большая часть методом является сокращением для методов хранилища.
    А также данные после изменения автоматически сохраняются.

    так что если ваша цель управлять несколькими пользователями, лучше
    это делать через хранилище пользователей, а не через данный класс.
    """

    def __init__(self, storage: FileUserStorage, uid: str) -> None:
        self.uid = uid
        self._storage = storage
        self.data = self._storage.get_user(uid)

    def create(self) -> None:
        """Создает пользователя.

        Также как и с хранилищем пользователя может как создать
        пользователя, так и перезаписать данные до значений по
        умолчанию.
        """
        self._storage.create_user(self.uid)
        self._storage.save_users()
        self.data = self._storage.get_user(self.uid)

    def remove(self) -> None:
        """Удаляет пользователя.

        В отличие от метода хранилища, которое напрямую удаляет данные
        пользователя,
        данный метод не удалит пользователя, если он не существует.
        """
        if self.data is not None:
            self._storage.remove_user(self.uid)
            self._storage.save_users()
            self.data = UserData()

    def set_class(self, cl: str, sc: Schedule) -> bool:
        """Устанавливает класс пользователя.

        Если класс будет установлен, то сохраняет данные хранилища.
        Также как и с методов хранилищаЮ, возвращает статус смены
        класса.

        - Класс будет установлен на заданный.
        - Флаг установленного класса станет True.
        - Время последней проверки станет временем проверки расписания.
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
        Это нужно чтобы прочие настройки пользователя были не тронуты.
        """
        self._storage.unset_class(self.uid)
        self._storage.save_users()
        self.update()

    def save(self, save_users: bool | None = True) -> None:
        """Сохраняет текущие локальные данные пользователя.

        .. deprecated:: 6.0

            Данные метод может быть в любое время удалён.
            Поскольку логично его не должно быть.
        """
        self._storage.update_user(self.uid, self.data)
        if save_users:
            self._storage.save_users()

    def update(self) -> None:
        """Получает данные пользователя из хранилища."""
        self.data = self._storage.get_user(self.uid)

    def get_updates(
        self, sc: Schedule, save_users: bool = True
    ) -> dict[str, int | list[dict]] | None:
        """Возвращает компактную запись о всех новых обновлениях.

        Получает все новые записи об изменениях в расписании, начиная
        с текущей отметки ``last_parse`` пользователя.
        Все записи об изменениях сживаются при помощи
        :py:func:`sp.sp.utils.compact_updates`.
        После получения всех изменений, метка последней проверки
        сдвигается до времени последней записи об изменениях.

        .. note:: Хранилище изменений

            В скором времени этот метод будет перенесён в хранилище
            списка изменений.
        """
        if self.data.cl is None:
            return None

        if sc.schedule["last_parse"] <= self.data.last_parse:
            return None

        logger.info("Get lessons updates")
        i = Intent.construct(sc, cl=[self.data.cl])
        updates = sc.get_updates(i, self.data.last_parse)

        # Обновление времени последней проверки расписания
        self.data = UserData(
            create_time=self.data.create_time,
            cl=self.data.cl,
            set_class=self.data.set_class,
            last_parse=sc.schedule["last_parse"],
            notifications=self.data.notifications,
            hours=self.data.hours,
        )
        self.save(save_users)

        if len(updates) != 0:
            return compact_updates(updates)
        return None

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
            hours=self.data.hours,
        )
        self.save()

    def set_notify_off(self) -> None:
        """Отключает уведомления пользователя."""
        self.data = UserData(
            create_time=self.data.create_time,
            cl=self.data.cl,
            set_class=self.data.set_class,
            last_parse=self.data.last_parse,
            notifications=False,
            hours=self.data.hours,
        )
        self.save()

    def add_notify_hour(self, hour: int) -> None:
        """Добавляет рассылку в указанный час.

        Обратите внимание что на данный момент не происходит
        валидации числовых значений, так что самостоятельно убедитесь
        что вы передаёте час от 6-ти утра и 20-ти вечера.
        """
        if hour not in self.data.hours:
            self.data.hours.append(hour)
            self.save()

    def remove_notify_hour(self, hour: int) -> None:
        """Удаляет рассылку расписания в указанное время.

        Обратите внимание что на данный момент не происходит
        валидация числовых значений.
        Если вы попытаетесь выключить уведомления для того времени,
        которое ранее не было установлено, то получите исключение.
        """
        if hour in self.data.hours:
            self.data.hours.remove(hour)
            self.save()

    def reset_notify(self) -> None:
        """Сбрасывает часы рассылка расписания пользователя."""
        self.data = UserData(
            create_time=self.data.create_time,
            cl=self.data.cl,
            set_class=self.data.set_class,
            last_parse=self.data.last_parse,
            notifications=self.data.notifications,
            hours=[],
        )
        self.save()
