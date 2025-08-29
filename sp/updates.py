"""Модуль работы со списком обновлений."""

from typing import Any, TypedDict

# TODO: Дать более точные типа
WeekUpdatesT = list[dict[str, list[dict[str, Any]]]]


class UpdateData(TypedDict):
    """Что представляет собой запись об обновлении расписания."""

    start_time: int
    end_time: int
    updates: WeekUpdatesT


# TODO: В надеждах когда-нибудь переписать эту страшную функцию
# А пока работает и не трогаем, хе-хе ...
def compact_updates(updates: list[UpdateData]) -> UpdateData:
    """Упаковывает несколько записей об обновлениях в одну.

    Используется чтобы совместить несколько записей об изменениях.
    Например чтобы показать все изменения в расписании за неделю.
    Или использовать при получении обновлений расписания для
    пользователя.

    **Правила совмещения**:

    - Если урока ранее не было -> добавляем урок.
    - Если Урок A, сменился на B, а после снова на A -> удаляем урок.
    - Если A -> B, B -> C, то A => C.
    - Иначе добавить запись.
    """
    res: WeekUpdatesT = updates[0]["updates"].copy()

    # Просматриваем все последующии записи об обновлениях
    for update_data in updates[1:]:
        for day, day_update in enumerate(update_data["updates"]):
            for cl, cl_updates in day_update.items():
                if cl not in res[day]:
                    res[day][cl] = cl_updates
                    continue

                old_lessons = res[day][cl]
                new_lessons: list[tuple | None] = []

                for i, lesson in enumerate(cl_updates):
                    old_lesson = old_lessons[i]

                    # Если нет старого и нового урока.
                    if old_lesson is None and lesson is None:
                        new_lessons.append(None)

                    # Если появился новый урок
                    elif old_lesson is None and lesson is not None:
                        new_lessons.append(lesson)

                    # Совмещение записей об изменении уроков
                    elif lesson is None and old_lesson is not None:
                        new_lessons.append(old_lesson)

                    # B -> A, C -> A = None
                    elif (
                        old_lesson[1] == lesson[1] or old_lesson[0] == lesson[1]
                    ):
                        new_lessons.append(None)

                    # A -> B; B -> C = A -> C
                    elif old_lesson[1] == lesson[0]:
                        new_lessons.append((old_lesson[0], lesson[1]))

                    else:
                        new_lessons.append(lesson)

                if new_lessons == [None] * 8:
                    del res[day][cl]
                else:
                    res[day][cl] = new_lessons

    return {
        "start_time": updates[0]["start_time"],
        "end_time": updates[-1]["end_time"],
        "updates": res,
    }
