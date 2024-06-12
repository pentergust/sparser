"""Класс описания платформы.

Более высокоуровневый класс, замена SPMessages.
Проводником между пользователем и расписанием является некотороая
платформа-посредник.
Это может быть как Telegram бот, web-приложение или просто консоль.
Данный модуль помогает настроить платформу, коотрая будет иметь
доступ к расписанию.
"""


from sp.exceptions import ViewNotCompatible, ViewNotSelected
from sp.messages import SPMessages
from sp.users.storage import FileUserStorage, User
from sp.users.intents import UserIntentsStorage

from loguru import logger


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
        self.users = FileUserStorage(f"sp_data/users/{name}.json")
        self._view = None


    # Работа с классом просмотра
    # ==========================

    def _check_api_version(self, api_verion: int) -> bool:
        if api_verion < self.api_version:
            raise ViewNotCompatible("Platform API is higher than view API")
        elif api_verion == self.api_version:
            return True
        else:
            logger.warning("Platform API is lower than view")
            logger.warning("Some functions may not work correctly.")
            return False

    @property
    def view(self) -> SPMessages | None:
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
        :py:class:`sp.exceptions.ViewNotSelected`.

        .. caution:: Почему SPMessages?

            Не смотря на то, что речь идёт о классе предствления,
            на выходе мы получаем ``SPMessages``.
            Это связано с тем, что сейчас SPMessages явдяется
            прородителем будухи классов представления.

        :raises ViewNotSelected: Если класс представления не установлен.
        :return: Текущий класс предсталвения платформы.
        :rtype: SPMessages | None
        """
        if self._view is not None:
            return self._view
        else:
            raise ViewNotSelected("Yot must set View before use it")

    @view.setter
    def view(self, view: SPMessages) -> None:
        if not isinstance(view, SPMessages):
            return
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

