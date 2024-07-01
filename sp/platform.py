"""Класс описания платформы.

Более высокоуровневый класс, замена SPMessages.
Проводником между пользователем и расписанием является некотороая
платформа-посредник.
Это может быть как Telegram бот, web-приложение или просто консоль.
Данный модуль помогает настроить платформу, коотрая будет иметь
доступ к расписанию.
"""

from typing import Any

from loguru import logger

from sp.exceptions import ViewCompatibleError, ViewSelectedError
from sp.intents import Intent
from sp.messages import SPMessages
from sp.users.intents import UserIntentsStorage
from sp.users.storage import FileUserStorage, User


class Platform():
    """Описание платформфы, на котороы було запущено расписание.

    более высокоуровневый класс абстракции.
    Позволяет получить доступ к внутренним хранилищам и методам класса
    представления.

    Подключает пользовательское хранилище.
    Настраивает класс представления и проверяет его совместимость.
    Реализует на их основе собственные методы для доступа
    к классу представления от лица конкретного пользователя.

    Platform ID используется для разграничения пользователей
    разных платформы.
    Название платформы будет использоваться в пути к хранилищам.

    :param pid: Уникальный id платформы.
    :type pid: int
    :param name: Название платформы.
    :type name: str
    :param version: Строковое описание версии платформы.
    :type version: str
    :param api_version: Поддверживаемая версия API представления.
    :type api_verion: int
    """

    def __init__(self, pid: int, name: str, version: str, api_version: int):
        self.pid = pid
        self.name = name
        self.version = version
        self.api_version = api_version

        #: Экземпляр хранилища пользователей платформы
        self.users = FileUserStorage(f"sp_data/users/{pid}.json")
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
        """Получает уттановленынй класс представления.

        Предполагается что перед тем как использовать класс предсталвния
        он будет установлен при помощи соотвествеющего сеттера.
        Класс представления может варьироваться в зависимости от
        платформы, однако поскольку они реализуют одинаковые методы,
        мы можем напрямую использовать методы класса представления.

        Однако просим орбратить внимание, что лучше использвать методы
        платформы, которые работают поверх методов класса представления,
        тем самым несколько упрощая нам жизнь.

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
        """Получает пользователя из встроенного хранилища.

        Позвоялет быстро получить класс для управления пользователем
        внутреннего хранилища платформы.
        Пользователь платформы досаточно часто используется в методах
        платфрмы.

        :param uid: ID пользователя в рамках платформы.
        :type uid: str
        :return: Класс управления пользователем внутреннего хранилища.
        :rtype: User
        """
        return User(self.users, uid)

    def get_intents(self, uid: int) -> UserIntentsStorage:
        """Возвращает экземпляр хранилища намерений пользователя.

        Как и с методом для получения класс User.
        Использую хранилище намерений вы сможете упрвлять своими
        намерениями.
        Добалять именные намерения, изменять и удалять их.
        Пользовательские намерения вскоре заменят класс по умолчанию.
        Постепенно у вас появится больше возможностей по выбору
        намерений в рамках одной платформы.

        :param uid: ID пользователя в рамках платформы.
        :type uid: int
        :return: Класс пользовательского хранилища намерений.
        :rtype: UserIntentsStorage
        """
        return UserIntentsStorage(f"sp_data/users/{self.pid}.db", uid)

    # Сокращения для методов класса представления
    # ===========================================

    def lessons(self, user: User, intent: Intent) -> Any:
        """Отправляет расписание уроков.

        Является сокращение для метода ``Platform.view.send_lessons()``.

        Для уточнения формата расписания принимает экземпляр намерения.
        А также пользователя, которые собирается получить расписание.

        :param intent: Намерения для уточнения параметров расписания.
        :type intent: Intent
        :param user: Кто хочет получить расписание уроков.
        :type user: User
        :return: Рузельтат работы метода в звисимости от платформы.
        :rtype: Any
        """
        return self.view.send_lessons(intent, user)

    def today_lessons(self, user: User, intent: Intent) -> Any:
        """Расписание уроков на сегодня/завтра.

        Сокращение для метода ``Platform.view.send_today_lessons()``.

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
        :rtype: Any
        """
        return self.view.send_today_lessons(intent, user)

    def search(
        self,
        target: str,
        intent: Intent,
        cabinets: bool = False
    ) -> Any:
        """Поиск в расписании по уроку/кабинету.

        Является сокращением для ``Platform.view.search()``.

        Производит поиск в расписании.
        А после собирает сообщение с результатами поиска.

        Поиск немного изменяется в зависимости от режима.

        .. table::

            +----------+---------+---------+
            | cabinets | obj     | another |
            +==========+=========+=========+
            | false    | lesson  | cabinet |
            +----------+---------+---------+
            | true     | cabinet | lesson  |
            +----------+---------+---------+

        :param target: Цель для поиска, название урока или кабинета.
        :type target: str
        :param intent: Намерение для уточнения результатов поиска.
        :type intent: Intent
        :param cabinets: Что ищём, урок или кабинет. Обычно урок.
        :type cabinets: bool
        :return: Результаты поиска в зависимости от платформы.
        :rtype: Any
        """
        return self.view.search(target, intent, cabinets)
