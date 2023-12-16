# SParser

> Парсер школьного расписания уроков.

![](_images/telegram.png)

Способ **быстро и удобно** просматривать расписание уроков.
Предоставляет **парсер** расписания из гугл таблиц.
Инструменты для расширения функционала класса рассписания.
Telegram (фото выше) и Vk бота для доступа к расписанию.


## Установка

Скопируйте репозиторий проекта:
```bash
git clone https://notabug.org/milinuri/sparser
cd sparser
```

### Установка зависимостей

Через [poetry](https://python-poetry.org/):
```bash
# Только парсер и генератор сообщений
poetry install

# Для разных обёрток
poetry install --with telegram
```

Через pip + Python venv:
```bash
# Создаём и активируем виртуальное окружение
# Запускать проект нужно тоже из виртуального окрежения
python -m venv venv
source venv/bin/activate

# Устанавливаем все зависимости
pip install -r requirements.txt
```

## Запуск

На примере Telegran бота. (`v2.0 (sp v5.7)`).
Перед первым запуском скопируйте файл `.env.dist` в `.env`.
В файле `.env` укажите ваш Telegram токен бота.

```toml
# .env
TELEGRAM_TOKEN=YOUR_TELEGRAM_TOKEN_HERE
```

После указания токена вы можете запускать бота.

Через Poetry:
```
poetry run python telegram.py
```

Через Python venv.
```sh
source venv/bin/activate
python telegram.py
```


## Чат-боты

### Telegram

Первую версию написал Артём Березин, положив начало проекту.

Разумеется, новая версия не имеет ничего общего с оригиналом.
Взаимодействие с ботом проиходит через запросы или клавиатуру.

В **текстовых запросах** вы указываете что вам нужно получить.
Будь то расписание для класса, урока или кабинета.
Вы можете уточнить свои запросы днём, классом, кабинетом, уроком.
Порядрок аргуметов в запроссе не важен, развлекайтесь.

**Клавиатура бота** позволяет дотянутся до всех основных разделов.
Вам не нужно писать однотипные запросы или вводить каждый раз команды.

Также для доступа к осноным разделам вы можете использовать команды.

### vk (устарел)

![](_images/vk.png)

> Ждёт своей очереди для обновения на последную версию sp

Повторяет функционал Telegam бота.

Вы так же можете использовать **текстовые запросы**.
**Клавиатура бота** в отличие от Telegram бота не прибита к сообщению,
а находится отдельно.
Это позоляет управлять всем ботов целиком, а не привзяываться к
отдельному сообщению.

[Статья о боте](https://vk.com/@chiorin-kak-poluchit-raspisanie).

### Некоторые ограничения

Не смотря на почти полную поддержку генератора сообщений, существуют
некоторые ограничения, наложенные оболочками чат-ботов.

Разделы на скриншоте:
- Смена класса.
- Главное меню (справка).
- Результат запроса к расписанию.
- Информация о парсере.

**Настройка намерений**:
Пока нет возможности полноценно представить намерения через клавиатуру.
Это отражается на списке изменений и счётчиках.
Однако это не столь критично для большинства пользователей ботов.

**Ограничение длинны сообещний**.
Приходится соблюдать баланс между информативностью и читаемостью.
Порой это не всегда получается что сказывается на удобсте использования.


## Консоль

![](_images/spm_console.png)

Простая обёртка для работы с генератором сообщений.
Имеет достаточно простой интерфейс.
Не требует установки дополнительных зависимостей.
Использует все основные методы генератора сообщений.
Будет полезен для отладки работы парсера и генератора сообщений.
А также как пример кода для написания ваших собственных обёрток.

Вот пример некоторых команд:
```bash
# Получить справку по командам
python spm_console.py --help

# Установка класс по умолчнию
python spm_console.py --set-class 8а

# Быстрое получение расписания (если указан класс)
python spm_console.py
```


## Возможности парсера

На одном парсере всё не заканчивается.
В проекте представлен класс `sp.parser.Schedule` для работы с расписанием.
Например для поиска уроков/кабинетов и просмотра списка изменений.

Также представлен генератор сообщений (`sp.messages`).
В нём находятся различные функции и класс `SPMessages`, для преобразования
результатов работы `Schedule` в текстовые сообщения например для чат-ботов.

Если вы хотите создать своего чат-бота, который бы отправлял расписание,
проще использовать готовый генератор сообщений.
Вам лишь остаётся прописать логику самого чат-бота, не задумываясь о
работе парсера и генератора сообщений.
Для примера использования генератора сообщений вы можете взглянуть на
`telegram.py` или `spcli.py`.

***

Главная задача парсера - преобразовать расписание из гугл таблиц.
Кратко: **Гугл таблицы** -> **CSV** -> **json**.

Для повышения скорости работы, все результаты работы хранятся в `sp_data/`.

`sp.counters` Счётчики для расписания:

- Предоставляет функции для подсчёта объектов в расписании.
- Доступные счётчики:
  - По классам: дни, уроки, кабинеты.
  - По дням: классы, уроки, кабинеты.
  - По индексам: уроки/кабинеты.
    - Уроки: классы, дни, кабинеты.
    - Классы: уроки, дни, кабинеты.
- Все счётчики используют фильтры для уточнения подсчётов.

`sp.intents` Намерения:

- Предоставляет класс намерений для уточнения результатов запросов.
- Используются в большинстве методах парсера и генератора сообщений.
- Имеется конструктор намерений:
  - Принимает классы, дни, уроки, кабинеты.
- Имеется парсер, преобразующий строковые аргументы в намерения.
  - Пример запроса: "Уроки для 7а на вторник, среду"

`sp.messages` Генератор сообщений:

- Отображение списка изменений в расписании.
- Отображения списка уроков.
  - С указанием номера урока, расписания звонков.
  - Указатель на текущий урок.
- Отображение результатов поиска в расписании.
- Отображение сгруппированных результатов счётчика.
- Отображения отладочной информации о парсере и генераторе сообщений.
- Управление данными пользователя по их `User ID`:
  - Получение данных пользователя.
  - Сохранение данных пользователя.
  - Сброс данных до значений по умолчанию.
  - Установка класса по умолчанию.
- Отправка расписания уроков. (использует намерения)
  - Отображение изменений в расписании пользователя при наличии.
- Отправка расписания уроков на сегодня/завтра. (использует намерения)

`sp.parser` Парсер:

- Отслеживание изменений во всём расписании.
- Получение индексов расписания (`l_index`, `c_index`).
  - Словарь по урокам/кабинетом.
  - Какие, когда, где и для кого проводятся уроки/кабинеты.
- Парсер уроков (`CSV -> Dict`).
- Умное обновление расписания.
  - Ежечасное сравнение хешей расписания.
  - Если хеши расписаний отличаются - начинается процесс обновления.
  - Обновляется расписание, индексы, список изменений.
  - Результаты работы сохраняются в `sp_data/`.
- Получение списка уроков для выбранного класса.
- Получение списка обновлений в расписании (использует фильтры).
- Поиск данных в расписании (использует фильтры).
