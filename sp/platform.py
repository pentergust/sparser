"""Класс платформы.

Более высокоуровневый класс, замена SPMessages.
Проводником между пользователем и расписанием является некотороая
платформа-посредник.
Это может быть как Telegram бот, web-приложение или просто консоль.
Данный модуль помогает настроить платформу, коотрая будет иметь
доступ к расписаниям.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from loguru import logger

from sp.counter import CounterTarget
from sp.enums import WeekDay
from sp.exceptions import ViewCompatibleError, ViewSelectedError
from sp.intents import Intent
from sp.messages import SPMessages
from sp.users.intents import UserIntentsStorage
from sp.users.storage import FileUserStorage, User

# Главный класс платформы
# =======================

class Platform:
    """Платформа для предоставления расписания.

    Более высокоуровеневый класс.
    Предоставляет доступ к классу представления пользователя,
    хранилищу пользователей плафтормы и пользовательским намерениям.

    Platform ID используется для разграничения пользователей
    разных платформы.
    Название платформы будет использоваться в пути к хранилищам.

    :param pid: Уникальный id платформы.
    :type pid: int
    :param name: Название платформы.
    :type name: str
    :param version: Строковое описание версии платформы.
    :type version: str
    :param api_version: Подддерживаемая версия API представления.
    :type api_verion: int
    """

    def __init__(self, pid: int, name: str, version: str, api_version: int):
        self.pid = pid
        self.name = name
        self.version = version
        self.api_version = api_version

        self._file_path = Path(f"sp_data/users/{pid}.json")
        self._db_path = Path(f"sp_data/users/{pid}.db")
        #: Экземпляр хранилища пользователей платформы
        self.users = FileUserStorage(self._file_path)
        self._view: SPMessages | None = None


    # Работа с классом просмотра
    # ==========================

    def _check_api_version(self, api_verion: int) -> bool:
        if api_verion < self.api_version:
            raise ViewCompatibleError("Platform API is higher than view API")
        elif api_verion == self.api_version:
            return True
        else:
            logger.warning("Platform API is lower than view")
            logger.warning("Some functions may not work correctly.")
            return False

    @property
    def view(self) -> SPMessages:
        """Получает текущий класс представления.

        Предполагается что перед тем как использовать класс предсталвния
        он будет установлен при помощи соотвествеющего сеттера.
        Класс представления может варьироваться в зависимости от
        платформы, однако поскольку они реализуют одинаковые методы,
        мы можем напрямую использовать методы класса представления.

        Однако просим орбратить внимание, что лучше использвать методы
        платформы, которые работают поверх методов класса представления,
        тем самым несколько упрощая жизнь.

        Если вы попытаетесь получить класс представления до того как
        он был задан явно, то вы получите исключение
        :py:class:`sp.exceptions.ViewSelectedError`.

        .. caution:: Почему SPMessages?

            Не смотря на то, что речь идёт о классе предствления,
            на выходе мы получаем ``SPMessages``.
            Это связано с тем, что сейчас SPMessages явдяется
            прородителем будухи классов представления.

        :raises ViewSelectedError: Если класс представления не установлен.
        :return: Текущий класс предсталвения платформы.
        :rtype: SPMessages | None
        """
        if self._view is not None:
            return self._view
        else:
            raise ViewSelectedError("Yot must set View before use it")

    @view.setter
    def view(self, view: SPMessages) -> None:
        if not isinstance(view, SPMessages):
            raise ViewCompatibleError("View must be instance of SPMessages")
        self._check_api_version(view.API_VERSION)
        self._view = view


    # Получение хранилищ пользователей
    # ================================

    def get_user(self, uid: str) -> User:
        """Получает пользователя из хранилища пользователей.

        Позвоялет быстро получить класс для управления пользователем
        внутреннего хранилища платформы.
        Пользователь платформы досаточно часто используется в методах
        платфрмы.

        :param uid: ID пользователя в рамках платформы.
        :type uid: str
        :return: Конкретный пользователь хранилиша.
        :rtype: User
        """
        return User(self.users, uid)

    def get_intents(self, uid: int) -> UserIntentsStorage:
        """Возвращает экземпляр хранилища намерений пользователя.

        Подобно получения пользователя платформы, получает намерения.
        Добалять именные намерения, изменять и удалять их.
        Пользовательские намерения вскоре заменят класс по умолчанию.
        Постепенно у вас появится больше возможностей по выбору
        намерений в рамках одной платформы.

        :param uid: ID пользователя в рамках платформы.
        :type uid: int
        :return: Класс пользовательского хранилища намерений.
        :rtype: UserIntentsStorage
        """
        return UserIntentsStorage(self._db_path, uid)

    # Сокращения для методов класса представления
    # ===========================================

    def _get_user_intent(
        self,
        user: User,
        intent: Intent | None=None
    ) -> Intent:
        if intent is None:
            if user.data.cl is None:
                raise ValueError("User class is None")
            return self.view.sc.construct_intent(cl=user.data.cl)
        return intent

    def lessons(self, user: User, intent: Intent | None=None) -> str:
        """Отправляет расписание уроков.

        Является сокращение для метода ``SPMessages.send_lessons()``.
        Принимает пользователя, желающего получить расписание, а также
        намереие для уточнения резултата.
        Если намерение не было передано, будет взят класс пользователя.

        :param user: Кто хочет получить расписание уроков.
        :type user: User
        :param intent: Намерения для уточнения параметров расписания.
        :type intent: Optional[Intent]
        :return: Рузельтат работы метода в звисимости от платформы.
        :rtype: str
        """
        return self.view.send_lessons(self._get_user_intent(user, intent))

    def today_lessons(self, user: User, intent: Optional[Intent]=None) -> str:
        """Расписание уроков на сегодня/завтра.

        Сокращение для метода ``SPMessages.send_today_lessons()``.

        Работает как send_lessons.
        Отправляет расписание для классов на сегодня, если уроки
        ешё идут.
        Отпрвялет расписание на завтра, если уроки на сегодня уже
        кончились.

        Использует намерения для уточнения расписания.
        Однако будет игнорировать указанные дни в намерении.
        Иначе используйте метод send_lessons.

        :param intent: Намерения для уточнения расписания.
        :type intent: Intent
        :param user: Кто хочет получить расписание уроков.
        :type user: User
        :return: Результат в зависимости от класса предсталвения.
        :rtype: str
        """
        return self.view.send_today_lessons(self._get_user_intent(user, intent))


    def current_day(self, user: User, intent: Intent | None = None) -> int:
        """Получает текщий день в расписании.

        Сокращение для: ``SPMessages.get_current_day()``.
        Если урока для указанного пользователя ещё идут, вернут сегодня,
        иначе же вернёт завтрашний день.

        Передаётся пользователь, а также намерение для получения
        расписаниея.
        Если намерение не было передано то получает класс пользовтеля.

        :param user: Какой пользователь захотел получить текщий день.
        :type user: User
        :param inent: Намеренеи для уточнения расписнаия (классы).
        :type intent: Intent | None
        :return: Текущий день недели для расписаниея.
        :rtype: int
        """
        return self.view.get_current_day(self._get_user_intent(user, intent))

    def _get_day_str(self, today: int, relative_day: str) -> str:
        if relative_day == today:
            return "Сегодня"
        elif relative_day == today+1:
            return "Завтра"
        else:
            return WeekDay(relative_day).to_short_str()

    def relative_day(self, user: User) -> str:
        """Получает строковое название текущего дня недели.

        Оптимизированная функция, похожа ``Platform.current_day()``.
        Возвращает Сегодня/Завтра/день недели, в зависимости от
        прошедших уроков.

        Не принимает намерение, получает день только для
        переданного опльзователя.

        :param user: Для какого пользователя получаем расписание.
        :type User: User
        :return: Сегодня/Завтра/день недели.
        :rtype: str
        """
        today = date.today().weekday()
        tomorrow = today + 1
        if tomorrow > WeekDay.SATURDAY:
            tomorrow = 0

        if user.data.cl is None:
            return "Сегодня"

        current_day = self.view.get_current_day(
            intent=self.view.sc.construct_intent(cl=user.data.cl, days=today)
        )
        return self._get_day_str(today, current_day)


    def search(
        self,
        target: str,
        intent: Intent,
        cabinets: bool = False
    ) -> str:
        """Поиск в расписании по уроку/кабинету.

        Является сокращением для ``SPMessages.search()``.
        Результаты поиска собираются в нужный формат.

        Поиск немного изменяется в зависимости от режима.

        .. table::

            +----------+---------+---------+
            | cabinets | obj     | another |
            +==========+=========+=========+
            | false    | lesson  | cabinet |
            +----------+---------+---------+
            | true     | cabinet | lesson  |
            +----------+---------+---------+

        :param target: Цель для поиска, название урока/кабинета.
        :type target: str
        :param intent: Намерение для уточнения результатов поиска.
        :type intent: Intent
        :param cabinets: Что ищём, урок или кабинет. (урок).
        :type cabinets: bool
        :return: Результаты поиска в зависимости от платформы.
        :rtype: str
        """
        return self.view.search(target, intent, cabinets)

    def counter(
        self,
        groups: dict[int, dict[str, dict]],
        target: CounterTarget | None=None,
        days_counter: bool=False
    ) -> str:
        """Получает результаты работы счётчика.

        Сокращение для: ``SPMessages.send_counter()``.
        Используется чтобы преобразовать результаты счётчика к удобному
        формату отображения.

        .. code-block:: python

            from sp.parser import Schedule
            from sp.counter import CurrentCounter, CounterTarget

            sc = Schedule()
            cc = CurrentCounter(sc, sc.construct_intent())
            message = platform.send_counter(
                cc.cl(),
                CounterTarget.DAYS,
                daus_counter=True # Поскольку присутствуют дни недели
            )

        :param groups: Результаты работы счётчика.
        :type groups: dict[int, dict[str, dict]]
        :param target: Цель отображения расписания.
        :type target: CounterTarget | None
        :param days_counter: Следует ли заменять число на дни недели.
        :type days_counter: bool
        """
        return self.view.send_counter(groups, target, days_counter)

    def updates(self,
        update: dict[str, int | list[dict]],
        hide_cl: str | None=None
    ) -> str:
        """Собирает сообщение со списком изменений.

        Сокращение для: ``SPMessages.send_update()``.

        :param update: Запись об изменениях в расписании.
        :type update: dict[str, int  |  list[dict]]
        :param hide_cl: Какой заголовок класса прятать.
        :type hide_cl: Optional[str], optional
        :return: Запись с информации об изменениях в расписании.
        :rtype: str
        """
        return self.view.send_update(update, hide_cl)

    def check_updates(self, user: User) -> str | None:
        """Проверяет, нет ли у пользовталеей обновления расипсания.

        Сокращение для: ``SPMessages.check_update()``.
        Отправляет сжатую запись об измнениях в расписании, или None,
        если новых изменений нет.

        :param user: Для какого пользователя проверить обновления.
        :type user: User
        :return: Сжатая запись об изменениях или None, если их нет.
        :rtype: str | None
        """
        return self.view.check_updates(user)

    def status(self, user: User) -> str:
        """Отправялет статус работы платформы.

        Сокращение для: ``SPMessages.send_status()``.

        :param user: Для каого пользователя получить статистику.
        :type user: User
        :return: Информация о работе платформы.
        :rtype: str
        """
        count_result = self.users.count_users(self.view.sc)
        return self.view.send_status(count_result, user)
