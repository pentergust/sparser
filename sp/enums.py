from enum import IntEnum

DAY_NAMES = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота")
SHORT_DAY_NAMES = ("пн", "вт", "ср", "чт", "пт", "сб")

class WeekDay(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5

    def to_str(self) -> str:
        return DAY_NAMES[self.value]

    def to_short_str(self) -> str:
        return SHORT_DAY_NAMES[self.value]
