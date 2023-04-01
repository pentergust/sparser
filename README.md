# SParser

> Парсер школьного расписания уроков.

Цель - **быстрое и удобное** получения расписания уроков.
А так же постараться **выжать максимум** возможностей из расписания.


## Установка

На примере Telegram бота с расписанием.

Загрузите этот репозиторий (напрмиер через `git clone`).
Создайте виртуальное окружение и установите необходимые зависимости.

```bash
git clone https://notabug.org/milinuri/sparser
cd sparser
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python telegram.py
```

После первого запуска `telegram.py` у вас появится файл `sp_data/token.json`.
куда вы и должны будете указать токен от вашего Telegram бота.
После этого снова запустите бота и всё будет работать.


## Немного о sp v3.x

Помимо актуальной версии (`sp/`) вы также найдёте `sp v3.x (sp3/)`.
Данная версия считается устаревшей и не рекомендуется к использованию.
Тем не менее, в ней реализованы обёртки для консоли и Chio (ныне устаревшей).

> *Позднее все компоненты будут переписаны под актуальную версию sp.*


## Возможности парсера

На одном парсере всё не заканчивается.
В проекте представлен класс `sp.parser.Schedule` для работы с расписанием.
Например для поиска уроков/кабинетов и просмотра списка изменений. 

Также представлен генератор сообщений (`sp.spm`).
В нём находятся различные функции и класс `SPMessages`, для преобразования
результатов работы `Schedule` в текстовые сообщения например для чат-ботов.

Если вы хотите создать своего чат-бота, который бы отправлял расписание,
лучше использовать готовый генератор сообщений. 
Вам лишь остается прописать логику самого чат-бота.
Для примера использования генератора сообщений вы можете взглянуть на
`telegram.py` или `spm_console.py`.

Доступные обёртки:

- Telegram бот
- Консоль (spm_console, sp v3.x)
- Плагин Чио (ВК, sp v3.x) 


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

`sp.filters` Фильтры:

- Предоставляет датакласс фильтров для уточнения результатов.
- Используются в большинстве функций проекта.
- Имеется сборщик фильтров:
  - Принимает классы, дни, уроки, кабинеты.
- Имеется парсер, преобразующий строковые аргументы в фильтр
  - Пример запроса: "Уроки для 7а на вторник, среду"

`sp.parser` Парсер:

- Отслеживание изменений во всём расписании.
- Получение индексов расписания. (`l_index`, `c_index`)
  - Словарь по урокам/кабиентом.
  - Какие, когда, где, для кого проводятся уроки/кабинеты.
- Парсер уроков. (`CSV -> Dict`)
- Умное обновление расписания.
  - Ежечасное сравнение хешей расписания.
  - Если хеши расписаний отличаются - начинается процесс обновелния.
  - Обновляется расписание, индексы, список изменений.
  - Результаты работы сохраняются в `sp_data/`.
- Получение списка уроков для выбранного класса.
- Получение списка обновлений в расписаниии (использует фильтры).
- Поиск данных в расписании (использует фильтры).

`sp.spm` (Генератор сообщений):

- Отображение списка изменений в расписании.
- Отображения списка уроков.
  - С укзаанием номера урока, расписания звонков.
  - Указатель на текущий урок.
- Отображение результатов поиска в расписании.
- Отображение сгруппированных результатов счётчика.
- Отображения отладочной информации о сборке.
- Управление данными пользователя по их User ID:
  - Получени данных пользователя.
  - Сохранение данных пользователя.
  - Сброс данных до значений по умолчанию.
  - Установка класса по умолчанию.
- Отправка расписания уроков. (использует фильтры)
  - Отображение изменений в расписании пользователя при наличии.
- Отправка расписания уроков на сегодня/завтра. (использует фильтры)

Обёртки не всегда поддерживают все 100% `sp.spm`!


## Telegram

Оригинал написал Артём Березин, за что ему спасибо.
Новый бот полностью отличается от оригинала в лучшею сторону.
Разобраться в боте не составит особого труда.
Для вас есть удобная клавиатура, чтобы вы могли быстро получить расписние.
Реализована большая часть `SPMessages` (90%), с некоторыми ограничениями.

**Некоторые ограничения**:

Пока нет возможности полноценно представить фильтры через клавиатуру.
Это отражается на списке изменений и счётчиках.
Но это ограничение не столь критично для большинства пользователей.

Ограничение длинны сообещний. 
Приходится соблюдать баланс между информативностью и читаемостью.
Порой это не всегда получается что сказывается на удобсте использования.

Тем не менее, бот отлично подходит для решения большинства ваших задач.

Если вам нужны все 100% генератора сообщений, то обратитесь к консоли.


## Консоль

![](_images/spm_console.png)

**spm_console для sp v5.0**:

Поддерживает все 100% генератора сообщений.
Полезен для отладки и как пример использования генератора сообщений.

**Для sp v3.x**:

Поддерживает все 110% возможностей `sp v3.x`.
Собственный красивый генератор сообщений, ориентированный под консоль.
Когда-нибудь будет переписан под новую версию.


## Chio Plugin (sp v3.x)

![](_images/vk.png)

Поддерживаются 100% возможностей пасрера `v3.x`.
Реализация "ленивых" оповещений.
В установленное время (с опозданием...) прилетает расписание.
Как установить и запустить Чио описано в её собственном репозитории.
Довольно простые команды.
Вряд-ли будет переписано под новую версию.

**Чио более не обновляется.**

Команды плагина:

- `/автопост [выкл/ЧАС]`: Настройка автопоста расписания
- `/класс [cl]`: Изменить класс по умолчанию на `cl`
- `/уроки [args]`: Получить расписание:
  - Если аргументы не указаны, получаем уроки на сегодня/завтра для класса по умолчанию
  - Если указать **класс** - для выбранного класса
  - Если указать **дни недели** - на эти дни
  - Если указать **урок** - поиск по урокам
  - Комбинировать эти аргументы можно как вашей душе угодно
- `/расписание [args]`: Расписание на неделю
  - Если ничего не указать, получаем расписание на неделю для класса по умолчанию
  - Если указать **класс** - для выбранного класса
  - Если указать **"изменения"** - получаем изменения в расписании 
- `/sparser`: Информация о парсере
- `/clessons [cl]`: Самыек частые уроки (всего/класс)
- `/ccabinets [cl]`: Самые частые кабинеты (всего/класс)
