"""Класс, описывающий пользователя расписания.

Позволяет управлять как базой данных пользователей,
так и каждым пользователей в отдельности.
Используется вне зависимости от платформы, что повыщает переносимость.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional, Union

import ujson
# from icecream import ic
from loguru import logger

from sp.intents import Intent
from sp.parser import Schedule
from sp.utils import compact_updates


class UserData(NamedTuple):
    """Данные пользователя.

    create_time (int, Optional): Когда был создан аккаунт.
    cl (str, Optional): Класс пользователя
    set_class (bool): Установлен ли класс пользователя.
    last_parse (int): Время последней проверки расписания.
    notifications (bool): Включены ли уведомлений у пользователя.
    hours (list[int]): В какие часы рассылать отправлять уроков.
    """

    create_time: Optional[int] = int(datetime.now().timestamp())
    cl: Optional[str] = None
    set_class: Optional[bool] = False
    last_parse: Optional[int] = 0
    notifications: Optional[bool] = True
    hours: list[int] = []


class CountedUsers(NamedTuple):
    """Результат подсчёта пользователей.

    active (int): Сколько пользователей использую обёртку.
    cl (Counter): Счётчик классов пользователей.
    """

    active: int
    cl: Counter


class FileUserStorage:
    """Хранилище пользователей в JSON файле.

    Используется чтобы взаимодействовать с пользователями обёрток.
    Получать, добавлять, удалять, изменять пользователей.
    Содержит некоторые вспомогательные функции, кк например подсчёт
    пользователям по классам.

    Платформонезависимый класс, используется разными обёртками.

    path (str, Path): Путь к файлу пользователей.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self._path = Path(path)
        self._users: Union[dict[str, UserData], None] = None

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


    def get_users(self) -> dict[str, UserData]:
        if self._users is None:
            try:
                with open(self._path) as f:
                    users = ujson.loads(f.read())
            except FileNotFoundError as e:
                print(e)
                users = {}
            self._users = {
                k: self._dict_to_userdata(v) for k, v in users.items()
            }
        return self._users

    def save_users(self) -> None:
        users = {k: self._userdata_to_dict(v) for k, v in self._users.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            f.write(ujson.dumps(users))
        self._users = None

    def count_users(self, sc: Schedule) -> CountedUsers:
        if self._users is None:
            self.get_users()

        active_users = 0
        cl_counter = Counter()
        for k, v in self._users.items():
            cl_counter[v.cl] += 1
            if v.notifications and v.last_parse >= sc.schedule["last_parse"]:
                active_users += 1
        return CountedUsers(active_users, cl_counter)


    def create_user(self, uid: str) -> None:
        if self._users is None:
            self.get_users()
        self._users[uid] = UserData()

    def get_user(self, uid: str) -> UserData:
        if self._users is None:
            self.get_users()

        return self._users.get(uid, UserData())

    def remove_user(self, uid: str) -> None:
        if self._users is None:
            self.get_users()

        self._users.pop(uid, None)

    def set_class(self, uid: str, cl: Optional[str], sc: Schedule) -> bool:
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

    def update_user(self, uid: str, user: UserData) -> None:
        if self._users is None:
            self.get_users()

        self._users[uid] = user


class User:

    def __init__(self, storage: FileUserStorage, uid: str) -> None:
        self.uid = uid
        self._storage = storage
        self.data = self._storage.get_user(uid)

    def create(self) -> None:
        self._storage.create_user(self.uid)
        self.data = self._storage.get_user(self.uid)

    def remove(self) -> None:
        if self.data is not None:
            self._storage.remove_user(self.uid)
            self._storage.save_users()
            self.data = UserData()

    def set_class(self, cl: str, sc: Schedule) -> bool:
        res = self._storage.set_class(self.uid, cl, sc)
        if res:
            self._storage.save_users()
            self.data = self._storage.get_user(self.uid)
        return res

    def save(self, save_users: Optional[bool]=True) -> None:
        self._storage.update_user(self.uid, self.data)
        if save_users:
            self._storage.save_users()

    def get_updates(self, sc: Schedule, save_users: Optional[bool]=True
    ) -> list[dict[str, Union[str, dict]]]:
        """Возвращает дни, для которых изменилось расписание."""
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
        self,save(new_user, save_users)

        if save_users:
            self._storage.save_users()

        if len(updates) != 0:
            return compact_updates(updates)
        else:
            return

    # Настройки уведомлений
    # =====================

    def set_notify_on(self) -> None:
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
        if hour not in self.data.hours:
            self.data.hours.append(hour)
            self.save()

    def remove_notify_hour(self, hour: int) -> None:
        if hour in self.data.hours:
            self.data.hours.remove()
            self.save()

    def reset_notify(self) -> None:
        self.data = UserData(
                create_time=self.data.create_time,
                cl=self.data.cl,
                set_class=self.data.set_class,
                last_parse=self.data.last_parse,
                notifications=self.data.notifications,
                hours=[]
        )
        self.save()