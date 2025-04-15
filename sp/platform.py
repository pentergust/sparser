"""Класс платформы.

Более высокоуровневый класс, замена SPMessages.
Проводником между пользователем и расписанием является некоторая
платформа-посредник.
Это может быть как Telegram бот, web-приложение или просто консоль.
Данный модуль помогает настроить платформу, которая будет иметь
доступ к расписаниям.
"""

from datetime import date
from pathlib import Path

from loguru import logger

from sp.counter import CounterTarget
from sp.db import User
from sp.enums import WeekDay
from sp.exceptions import ViewCompatibleError, ViewSelectedError
from sp.intents import Intent
from sp.messages import SPMessages
from sp.parser import UpdateData
from sp.version import VersionInfo

# Главный класс платформы
# =======================


class Platform:
    """Платформа для предоставления расписания.

    Более высокоорганизованный класс.
    Предоставляет доступ к классу представления пользователя,
    хранилищу пользователей платформы и пользовательским намерениям.

    Platform ID используется для разграничения пользователей
    разных платформы.
    Название платформы будет использоваться в пути к хранилищам.

    :param pid: Уникальный id платформы.
    :param name: Название платформы.
    :param version: Строковое описание версии платформы.
    :param api_version: Поддерживаемая версия API представления.
    """

    def __init__(self, pid: int, name: str, version: VersionInfo) -> None:
        self.pid = pid
        self.name = name
        self.version = version

        self._file_path = Path(f"sp_data/users/{pid}.json")
        self._db_path = Path(f"sp_data/users/{pid}.db")
        self._view: SPMessages | None = None

    # Работа с классом просмотра
    # ==========================

    def _check_api_version(self, api_version: int) -> bool:
        if api_version < self.version.api_version:
            raise ViewCompatibleError("Platform API is higher than view API")
        elif api_version == self.version.api_version:
            return True
        else:
            logger.warning("Platform API is lower than view")
            logger.warning("Some functions may not work correctly.")
            return False

    @property
    def view(self) -> SPMessages:
        """Получает текущий класс представления.

        Предполагается что перед тем как использовать класс представления
        он будет установлен при помощи соответствующего сеттера.
        Класс представления может варьироваться в зависимости от
        платформы, однако поскольку они реализуют одинаковые методы,
        мы можем напрямую использовать методы класса представления.

        Однако просим обратить внимание, что лучше использовать методы
        платформы, которые работают поверх методов класса представления,
        тем самым несколько упрощая жизнь.

        Если вы попытаетесь получить класс представления до того как
        он был задан явно, то вы получите исключение
        :py:class:`sp.exceptions.ViewSelectedError`.

        .. caution:: Почему SPMessages?

            Не смотря на то, что речь идёт о классе представления,
            на выходе мы получаем ``SPMessages``.
            Это связано с тем, что сейчас SPMessages являются
            родоначальником будущих классов представления.
        """
        if self._view is not None:
            return self._view
        else:
            raise ViewSelectedError("Yot must set View before use it")

    @view.setter
    def view(self, view: SPMessages) -> None:
        if not isinstance(view, SPMessages):
            raise ViewCompatibleError("View must be instance of SPMessages")
        self._check_api_version(view.version.api_version)
        self._view = view

    # Сокращения для методов класса представления
    # ===========================================

    def _get_user_intent(
        self, user: User, intent: Intent | None = None
    ) -> Intent:
        if intent is None:
            if user.cl == "":
                raise ValueError("User class is None")
            return self.view.sc.construct_intent(cl=user.cl)
        return intent

    def lessons(self, user: User, intent: Intent | None = None) -> str:
        """Отправляет расписание уроков.

        Является сокращение для метода ``SPMessages.send_lessons()``.
        Принимает пользователя, желающего получить расписание, а также
        Намерения для уточнения результата.
        Если намерение не было передано, будет взят класс пользователя.
        """
        return self.view.send_lessons(self._get_user_intent(user, intent))

    def today_lessons(self, user: User, intent: Intent | None = None) -> str:
        """Расписание уроков на сегодня/завтра.

        Сокращение для метода ``SPMessages.send_today_lessons()``.

        Работает как send_lessons.
        Отправляет расписание для классов на сегодня, если уроки
        ешё идут.
        Отправляет расписание на завтра, если уроки на сегодня уже
        кончились.

        Использует намерения для уточнения расписания.
        Однако будет игнорировать указанные дни в намерении.
        Иначе используйте метод send_lessons.
        """
        return self.view.send_today_lessons(self._get_user_intent(user, intent))

    def current_day(self, user: User, intent: Intent | None = None) -> int:
        """Получает текущий день в расписании.

        Сокращение для: ``SPMessages.get_current_day()``.
        Если урока для указанного пользователя ещё идут, вернут сегодня,
        иначе же вернёт завтрашний день.

        Передаётся пользователь, а также намерение для получения
        расписания.
        Если намерение не было передано то получает класс пользователя.
        """
        return self.view.get_current_day(self._get_user_intent(user, intent))

    def _get_day_str(self, today: int, relative_day: int) -> str:
        if relative_day == today:
            return "Сегодня"
        elif relative_day == today + 1:
            return "Завтра"
        else:
            return WeekDay(relative_day).to_short_str()

    def relative_day(self, user: User) -> str:
        """Получает строковое название текущего дня недели.

        Оптимизированная функция, похожа ``Platform.current_day()``.
        Возвращает Сегодня/Завтра/день недели, в зависимости от
        прошедших уроков.

        Не принимает намерение, получает день только для
        переданного пользователя.
        """
        today = date.today().weekday()
        tomorrow = today + 1
        if tomorrow > WeekDay.SATURDAY:
            tomorrow = 0

        if user.cl == "":
            return "Сегодня"

        current_day = self.view.get_current_day(
            intent=self.view.sc.construct_intent(cl=user.cl, days=today)
        )
        return self._get_day_str(today, current_day)

    def search(
        self, target: str, intent: Intent, cabinets: bool = False
    ) -> str:
        """Поиск в расписании по уроку/кабинету.

        Является сокращением для ``SPMessages.search()``.
        Результаты поиска собираются в нужный формат.

        Поиск немного изменяется в зависимости от режима.

        +----------+---------+---------+
        | cabinets | obj     | another |
        +==========+=========+=========+
        | false    | lesson  | cabinet |
        +----------+---------+---------+
        | true     | cabinet | lesson  |
        +----------+---------+---------+
        """
        return self.view.search(target, intent, cabinets)

    def counter(
        self,
        groups: dict[int, dict[str, dict]],
        target: CounterTarget | None = None,
        days_counter: bool = False,
    ) -> str:
        """Получает результаты работы счётчика.

        Сокращение для: ``SPMessages.send_counter()``.
        Используется чтобы преобразовать результаты счётчика к удобному
        формату отображения.

        ```py
        from sp.parser import Schedule
        from sp.counter import CurrentCounter, CounterTarget

        sc = Schedule()
        cc = CurrentCounter(sc, sc.construct_intent())
        message = platform.send_counter(
            cc.cl(),
            CounterTarget.DAYS,
            days_counter=True # Поскольку присутствуют дни недели
        )
        ```
        """
        return self.view.send_counter(groups, target, days_counter)

    def updates(self, update: UpdateData, hide_cl: str | None = None) -> str:
        """Собирает сообщение со списком изменений.

        Сокращение для: ``SPMessages.send_update()``.
        """
        return self.view.send_update(update, hide_cl)

    async def check_updates(self, user: User) -> str | None:
        """Проверяет, нет ли у пользователей обновления расписания.

        Сокращение для: ``SPMessages.check_update()``.
        Отправляет сжатую запись об изменениях в расписании, или None,
        если новых изменений нет.
        """
        return await self.view.check_updates(user)

    async def status(self, user: User) -> str:
        """Отправляет статус работы платформы.

        Сокращение для: ``SPMessages.send_status()``.
        """
        count_result = await User.get_stats(self.view.sc)
        return self.view.send_status(count_result, user, self.version)
