"""Модели базы данных Postgres.

TODO: Переместить компонент на уровень бота.
"""

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from loguru import logger
from tortoise import Model, fields

from sp.intents import Intent
from sp.schedule import Schedule
from sp.updates import UpdateData, compact_updates

_HOUR_OFFSET = 6


@dataclass(slots=True, frozen=True)
class CountedUsers:
    """Результат подсчёта пользователей.

    Предоставляет статистические данные о хранилище пользователей.
    Сколько пользователей считаются активными (временная метка
    последнего обновления совпадает с расписанием),
    а также какие классы заданы у пользователей.
    Используется в методе для подсчёта количества пользователей.

    - `total` (int): Сколько всего пользователей платформы.
    - `notify` (int): Сколько пользователей включили уведомления.
    - `active` (int): Сколько пользователей использую платформу.
    - `cl` (Counter): Счётчик классов пользователей.
    - `hours` (Counter): счётчик времени отправки расписания.
    """

    total: int
    notify: int
    active: int
    cl: Counter[str | None]
    hour: Counter[int]


class UserIntent(Model):
    """Хранилище заготовленных намерений пользователя.

    - user: Какому пользователю принадлежат.
    - name: Строковое имя намерения.
    - intent: Запакованное в строку намерение.
    """

    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", "intents"
    )
    name = fields.CharField(max_length=64)
    intent = fields.TextField()


class User(Model):
    """Пользователь расписания.

    - `id`: Telegram ID пользователя.
    - `create_time`: Когда был зарегистрирован в боте.
    - `cl`: Выбранный пользователем класс или без привязки.
    - `set_class`: Устанавливал ли пользователь класс.
    - `notify`: Отправлять ли уведомлений пользователю.
    - `intents`: Намерения пользователя.
    """

    id = fields.BigIntField(pk=True)
    create_time = fields.DatetimeField(auto_now_add=True)
    update_tome = fields.DatetimeField(auto_now=True)
    last_parse = fields.DatetimeField(auto_now_add=True)
    # TODO: Перейти на использование намерений
    cl = fields.CharField(max_length=4, default="")
    set_class = fields.BooleanField(default=False)
    notify = fields.BooleanField(default=True)
    hours = fields.IntField(default=0)
    intents: fields.ReverseRelation[UserIntent]

    @classmethod
    async def get_stats(cls, sc: Schedule) -> CountedUsers:
        """Подсчитывает пользователей хранилища.

        Вспомогательная статистическая функция.
        Используется для сбора различной информации о пользователях.
        К примеру число пользователей, которые считаются активными.
        Также считает количество пользователей по классам.
        """
        all_users = await cls.all()

        total_users = len(all_users)
        notify_users = 0
        active_users = 0
        cl_counter: Counter[str | None] = Counter()
        hour_counter: Counter[int] = Counter()
        sc_last_parse = datetime.fromtimestamp(sc.schedule["last_parse"], UTC)

        for user in all_users:
            cl_counter[user.cl] += 1
            if user.notify:
                notify_users += 1

                for hour, status in user.get_hours():
                    hour_counter[hour] += 1

                if user.last_parse >= sc_last_parse:
                    active_users += 1

        return CountedUsers(
            total_users, notify_users, active_users, cl_counter, hour_counter
        )

    # TODO: Перейти на использование намерения
    async def set_cl(self, cl: str, sc: Schedule) -> bool:
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
        if cl == "" or cl in sc.lessons:
            self.cl = cl
            self.set_class = True
            self.last_parse = datetime.fromtimestamp(
                sc.schedule["last_parse"], UTC
            )
            await self.save()
            return True
        return False

    async def unset_cl(self) -> None:
        """Переводит пользователя в режим выбора класса.

        В отличие от полного сброса пользователя, некоторые параметры
        остаются не тронутыми.
        Потому предпочтительнее именно не сбрасывать данные, а снимать
        флаг выбора класса этим методом.

        - Снимает флаг выбора класса пользователя.
        - Сбрасывает класс по умолчанию.
        - Не трогает все остальные параметры пользователя.
        """
        self.cl = ""
        self.set_class = False
        await self.save()

    def get_hour(self, hour: int) -> bool:
        """Отправлять ли расписание в указанный час."""
        return bool(self.hours & (1 << hour - _HOUR_OFFSET))

    def set_hour(self, hour: int) -> None:
        """включает рассылку расписание в указанный час."""
        self.hours |= 1 << hour - _HOUR_OFFSET

    def reset_hour(self, hour: int) -> None:
        """Отключает рассылку расписания в указанный час."""
        self.hours &= ~(1 << hour - _HOUR_OFFSET)

    def get_hours(self) -> Iterator[tuple[int, bool]]:
        """Получает в какие часы включено расписание."""
        return ((hour, self.get_hour(hour)) for hour in range(6, 22))

    def reset_hours(self) -> None:
        """Сбрасывает часы отправка расписания."""
        self.hours = 0

    async def get_updates(self, sc: Schedule) -> UpdateData | None:
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
        if self.cl == "":
            return None

        if (
            datetime.fromtimestamp(sc.schedule["last_parse"], UTC)
            <= self.last_parse
        ):
            return None

        logger.info("Get lessons updates")
        i = Intent.construct(sc, cl=[self.cl])
        updates = sc.get_updates(i, int(self.last_parse.timestamp()))

        # Обновление времени последней проверки расписания
        self.last_parse = datetime.fromtimestamp(sc.schedule["last_parse"], UTC)
        await self.save()

        if len(updates) != 0:
            return compact_updates(updates)
        return None

    async def intent_or(self, intent: Intent | None = None) -> Intent:
        """Возвращает выбранное намерение или намерение по умолчанию.

        При фильтрации значений чтобы указать некоторое обязательное
        намерение.
        """
        return intent if intent is not None else await self.main_intent()

    async def main_intent(self) -> Intent:
        """Получает намерение пользователя по умолчанию.

        Оно заменяет собой параметр класса по умолчанию.
        Описывает что пользователю интереснее всего в расписании.
        Для учеников это обычно класс.
        для преподавателей может быть предмет.

        Для обратной совместимости пытается предоставить класс
        как намерение по умолчанию.
        В будущих версиях данный подход будет изменён.
        """
        intent_str = await self.intents.filter(name="main").get_or_none()
        if intent_str is not None:
            return Intent.from_str(intent_str.intent)

        if self.cl == "":
            raise ValueError("User not set class")
        return Intent(cl={self.cl})
