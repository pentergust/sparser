# sparser

> Парсер школьного расписания уроков.

Сколько времени уходит, чтобы просто посмотреть какие уроки на завтра?
Для начала нужно найти ссылку на расписание, хорошо если она лежит в закладках.
Потом ожидание пока расписание загрузится, поиск своего класса и наконец...

**Это долго!**

Главная цель проекта - максимальное **быстрое и удобное** получения расписания.

В этом репозитории:

- Парсер школьного расписания.
- Генератор текстовых сообщений для чат-ботов.
- **Консольный скрипт** для отладки и примера использования.
- Маленький **Telegram** бот.
- **Пллагин для Чио**, чтобы развернуть бота в **ВК**.


## О парсере

Парсер занимается переработкой содержимого гугл таблиц в "удобный" для использования формат.

Кратко: **Гугл таблицы** -> **CSV** файл -> **json** файл.

Выходной json файл (`sc.json`) содержит:

- Общий хеш расписания.
- В какой час была последняя проверка (0-23)
- Словарь уроков: {Класс: [{Уроки: [...] , Хеш: "ad4x..."}, {день 2}, ...]}
- Когда было последнее обновление расписания

Для повышения скорости результат работы парсера сохраняется в `sc.json`.
Раз в час происходит сравнение хешей и если отличаются - парсим.

Возможности парсера:

- Запоминает пользователей в `users.json`
- Пользователи для удобства могут указать класс по умолчанию
- Получить расписание для любого дня (дней) и класса
- Получение расписание на всю неделю для любого класса
- Получить оповещение об изменениях в их расписании
- Просмот изменений в расписании
- Просмотр самых частых уроков/кабинетов (и для класса)
- Поиск по уроку/кабинету (для кого, когда и где будет)


## Console

Поддерживает все 100% возможностей парсера.
Поставляется вместе с парсером.
Полезен для отладки и как пример использования.

```sh
# Просмотр справки по командам
python sparser/console.py --help
```

## Telegram

Оригинал написал Артём Березин, спасибо!
Всё происходит через клавиатуру бота и разобраться с ней труда не составит.

**Примечания**: 

- Разработка telegram бота затруднена т.к. у меня нету Telegram\`а :)
- Получить расписание для другого класса не сменив класс по умолчванию не получится
- Не получится получить расписание для нескольких дней. -> на всю неделю
- Не добпалено умное расписание на сегодня/завтра
- Не поддерживаются дополнительные функции парсера
- Нет поддержки последних функций парсера (частые уроки, поиск по уроку и т.д.)

Может будет разработан новый бот...


## Chio Plugin

Поддерживаются 100% возможностей пасрера.
Как установить и запустить Чио описано в её собственном репозитории.
Есть реализация "ленивого" автопоста расписания.
Довольно простые команды.

```sh
# Установка плагина
python cpm install sparser.packages/schedule
```
- `/автопост`: Настройка автопоста расписания
- `/класс [class_let]`: Изменить класс по умолчанию на `class_let`
- `/уроки [args]`: Получить расписание:
  - Если аргументы не указаны, получаем уроки на сегодня/завтра для класса по умолчанию
  - Если указать **класс**, получаем уроки **для выбранного класса**
  - Если указать **дни недели**, получаем уроки **на эти дни**
  - Если указать **урок**, будет произведён **поиск по урокам**
  - Комбинировать эти аргументы можно как вашей душе угодно
- `/расписание [args]`: Расписание на неделю
  - Если ничего не указать, получаем расписание на неделю для класса по умолчанию
  - Если указать класс, получаем расписание на неделю для этого класса
  - Если указать "изменения", получаем изменения в расписании 
- `/sparser`: Информация о парсере
- `/clessons [class_let]`: Самыек частые уроки (всего/класс) 

Более подробно, с примерами и скриншотами описано в группе [Чио](https://vk.com/chiorin).
