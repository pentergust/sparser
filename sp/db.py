"""Модели базы данных."""

from tortoise import Model, fields


class User(Model):
    """Пользователь расписания.

    - id: Telegram ID пользователя.
    - create_time: Когда был зарегистрирован в боте.
    - cl: Выбранный пользователем класс или без привязки.
    - set_class: Устанавливал ли пользователь класс.
    - notify: Отправлять ли уведомлений пользователю.
    - intents: Намерения пользователя.
    """

    id = fields.BigIntField(pk=True)
    create_time = fields.DatetimeField(auto_now_add=True)
    cl = fields.CharField(max_length=4)
    set_class = fields.BooleanField(default=False)
    notify = fields.BooleanField(default=True)
    intents: fields.ReverseRelation["UserIntent"]


class UserIntent(Model):
    """Хранилище заготовленных намерений пользователя.

    - user: Какому пользователю принадлежат.
    - name: Строковое имя намерения.
    - intent: Запакованное в строку намерение.
    """

    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.user", "intents"
    )
    name = fields.CharField(max_length=64)
    intent = fields.TextField()
