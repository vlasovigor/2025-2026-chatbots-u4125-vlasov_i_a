# 📊 Анализ взаимодействия с базой данных

## Обзор

Бот использует **SQLite** для сохранения результатов тестов пользователей. Все операции с БД асинхронные (async/await) с использованием библиотеки `aiosqlite`.

---

## 1. Структура БД

### Таблица `results`

```sql
CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    username    TEXT,
    first_name  TEXT,
    mode        TEXT NOT NULL,   -- 'general', 'topic', 'learning'
    topic       TEXT,            -- NULL для общего теста
    score       INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    date        TEXT NOT NULL
)
```

**Поля:**
- `id` - уникальный идентификатор записи
- `user_id` - Telegram ID пользователя (для связи с пользователем)
- `username` - @username пользователя (может быть NULL)
- `first_name` - имя пользователя
- `mode` - режим теста: `'general'`, `'topic'`, `'learning'`
- `topic` - ключ темы (только для тематического теста, иначе NULL)
- `score` - количество правильных ответов
- `total` - всего вопросов в тесте
- `date` - дата и время прохождения теста (формат: "DD.MM.YYYY HH:MM")

---

## 2. Функции работы с БД

### 2.1 `init_db()` - Инициализация БД

**Расположение:** `database.py`, строка 20

**Назначение:** Создание таблицы `results` при первом запуске бота

**Код:**
```python
async def init_db() -> None:
    """Инициализация базы данных: создание таблиц при первом запуске."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS results (...)
            """)
            await db.commit()
        logger.info(f"✅ База данных инициализирована: {DB_PATH}")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}", exc_info=True)
        raise
```

**Вызывается:** В функции `main()` при запуске бота (строка 852 в bot.py)

**Обработка ошибок:** ✅ Полная - логирует ошибку и пробрасывает исключение

---

### 2.2 `save_result()` - Сохранение результата теста

**Расположение:** `database.py`, строка 44

**Назначение:** Сохранение результата прохождения теста в БД

**Параметры:**
```python
async def save_result(
    user_id: int,           # Telegram ID
    username: str | None,   # @username
    first_name: str | None, # Имя
    mode: str,              # 'general', 'topic', 'learning'
    topic: str | None,      # Ключ темы
    score: int,             # Правильные ответы
    total: int,             # Всего вопросов
) -> None:
```

**Вызывается:** В функции `finish_quiz()` (строка 625 в bot.py)

**Код:**
```python
date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
try:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO results (user_id, username, first_name, mode, topic, score, total, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, first_name, mode, topic, score, total, date_str),
        )
        await db.commit()
    percent = round(score / total * 100) if total > 0 else 0
    logger.info(
        f"✅ Результат сохранён | user_id={user_id} | {first_name} | "
        f"mode={mode} | {score}/{total} ({percent}%)"
    )
except Exception as e:
    logger.error(f"❌ Ошибка сохранения результата для user_id={user_id}: {e}", exc_info=True)
    raise
```

**Обработка ошибок:** ✅ Полная - логирует ошибку и пробрасывает исключение

**Безопасность:** ✅ Использует параметризованные запросы (?) для защиты от SQL-инъекций

---

### 2.3 `get_user_results()` - Получение истории результатов

**Расположение:** `database.py`, строка 85

**Назначение:** Получение последних 10 результатов пользователя

**Параметры:**
```python
async def get_user_results(
    user_id: int,      # Telegram ID
    limit: int = 10    # Максимум записей
) -> list[dict]:
```

**Возвращает:** Список словарей с полями: `mode`, `topic`, `score`, `total`, `date`

**Вызывается:** В функции `show_results()` (строка 708 в bot.py)

**Код:**
```python
try:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT mode, topic, score, total, date
            FROM results
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            results = [dict(row) for row in rows]
    logger.debug(f"📊 Получены результаты | user_id={user_id} | найдено={len(results)} записей")
    return results
except Exception as e:
    logger.error(f"❌ Ошибка получения результатов для user_id={user_id}: {e}", exc_info=True)
    return []
```

**Обработка ошибок:** ✅ Полная - возвращает пустой список при ошибке

**Безопасность:** ✅ Параметризованные запросы

---

### 2.4 `get_user_stats()` - Получение статистики пользователя

**Расположение:** `database.py`, строка 115

**Назначение:** Получение агрегированной статистики пользователя

**Параметры:**
```python
async def get_user_stats(user_id: int) -> dict:
```

**Возвращает:** Словарь с полями:
- `total_tests` - количество пройденных тестов
- `total_correct` - всего правильных ответов
- `total_questions` - всего вопросов
- `avg_percent` - средний процент правильных ответов

**Вызывается:** В функции `show_results()` (строка 709 в bot.py)

**Код:**
```python
try:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT
                COUNT(*)                        AS total_tests,
                SUM(score)                      AS total_correct,
                SUM(total)                      AS total_questions,
                ROUND(AVG(CAST(score AS REAL) / total * 100), 1) AS avg_percent
            FROM results
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None or row[0] == 0:
                logger.debug(f"📊 Статистика пуста | user_id={user_id}")
                return {}
            stats = {
                "total_tests": row[0],
                "total_correct": row[1],
                "total_questions": row[2],
                "avg_percent": row[3],
            }
            logger.debug(
                f"📊 Статистика получена | user_id={user_id} | "
                f"тестов={row[0]} | средний результат={row[3]}%"
            )
            return stats
except Exception as e:
    logger.error(f"❌ Ошибка получения статистики для user_id={user_id}: {e}", exc_info=True)
    return {}
```

**Обработка ошибок:** ✅ Полная - возвращает пустой словарь при ошибке

**Безопасность:** ✅ Параметризованные запросы

---

## 3. Поток данных при прохождении теста

```
1. Пользователь нажимает "Пройти тест"
   ↓
2. Бот создает quiz state в context.user_data
   ↓
3. Пользователь отвечает на вопросы
   ↓
4. Бот считает score и собирает wrong_answers
   ↓
5. Тест завершен → вызывается finish_quiz()
   ↓
6. finish_quiz() вызывает save_result()
   ↓
7. save_result() вставляет запись в БД
   ↓
8. Бот показывает результат пользователю
   ↓
9. Пользователь может посмотреть /results
   ↓
10. show_results() вызывает get_user_results() и get_user_stats()
    ↓
11. Данные из БД отображаются пользователю
```

---

## 4. Обработка ошибок

### 4.1 В `finish_quiz()` (bot.py, строка 624-635)

```python
try:
    await save_result(...)
except Exception as e:
    logger.error(f"Ошибка сохранения результата: {e}")
```

**⚠️ ПРОБЛЕМА:** Ошибка логируется, но **не пробрасывается**. Это означает:
- Если БД недоступна, результат не сохранится
- Пользователь не узнает об ошибке
- Тест будет считаться завершенным

**Рекомендация:** Показать пользователю сообщение об ошибке

### 4.2 В `show_results()` (bot.py, строка 707-712)

```python
try:
    results = await get_user_results(user.id, limit=10)
    stats = await get_user_stats(user.id)
except Exception as e:
    logger.error(f"Ошибка получения результатов: {e}")
    results, stats = [], {}
```

**✅ ХОРОШО:** Ошибка обработана, пользователю показывается "У вас пока нет тестов"

---

## 5. Асинхронные операции

### Используемые паттерны:

**1. Context manager для подключения:**
```python
async with aiosqlite.connect(DB_PATH) as db:
    # Подключение автоматически закроется
```

**2. Context manager для курсора:**
```python
async with db.execute(...) as cursor:
    rows = await cursor.fetchall()
    # Курсор автоматически закроется
```

**3. Явный commit:**
```python
await db.execute(...)
await db.commit()  # Сохранить изменения
```

**✅ ХОРОШО:** Все операции правильно используют async/await

---

## 6. Целостность данных

### 6.1 Типы данных

| Поле | Тип | Проверка |
|------|-----|----------|
| `user_id` | INTEGER | ✅ Всегда передается |
| `username` | TEXT | ✅ Может быть NULL |
| `first_name` | TEXT | ✅ Может быть NULL |
| `mode` | TEXT | ✅ Проверяется в коде |
| `topic` | TEXT | ✅ Может быть NULL |
| `score` | INTEGER | ✅ Всегда >= 0 |
| `total` | INTEGER | ✅ Всегда > 0 |
| `date` | TEXT | ✅ Генерируется автоматически |

### 6.2 Валидация данных

**В `save_result()`:**
```python
percent = round(score / total * 100) if total > 0 else 0
```

**✅ ХОРОШО:** Проверка деления на ноль

**В `get_user_stats()`:**
```python
if row is None or row[0] == 0:
    return {}
```

**✅ ХОРОШО:** Проверка пустого результата

---

## 7. Производительность

### 7.1 Индексы

**⚠️ ПРОБЛЕМА:** Нет индексов на таблице `results`

**Рекомендация:** Добавить индекс на `user_id`:
```sql
CREATE INDEX idx_results_user_id ON results(user_id);
```

Это ускорит запросы `get_user_results()` и `get_user_stats()` при большом количестве записей.

### 7.2 Лимиты

**✅ ХОРОШО:** `get_user_results()` ограничивает результаты до 10 записей

---

## 8. Безопасность

### 8.1 SQL-инъекции

**✅ ЗАЩИЩЕНО:** Все запросы используют параметризованные запросы (?)

Пример:
```python
await db.execute(
    "INSERT INTO results (...) VALUES (?, ?, ?, ...)",
    (user_id, username, first_name, ...)
)
```

### 8.2 Конфиденциальность

**✅ ХОРОШО:** Данные пользователя изолированы по `user_id`

---

## 9. Логирование

### Уровни логирования:

| Функция | Уровень | Сообщение |
|---------|---------|-----------|
| `init_db()` | INFO | ✅ База данных инициализирована |
| `init_db()` | ERROR | ❌ Ошибка инициализации БД |
| `save_result()` | INFO | ✅ Результат сохранён |
| `save_result()` | ERROR | ❌ Ошибка сохранения результата |
| `get_user_results()` | DEBUG | 📊 Получены результаты |
| `get_user_results()` | ERROR | ❌ Ошибка получения результатов |
| `get_user_stats()` | DEBUG | 📊 Статистика получена |
| `get_user_stats()` | ERROR | ❌ Ошибка получения статистики |

**✅ ХОРОШО:** Подробное логирование с эмодзи для быстрого поиска

---

## 10. Рекомендации по улучшению

### 🔴 Критические

1. **Обработка ошибок в `finish_quiz()`**
   - Показать пользователю сообщение об ошибке сохранения
   - Предложить повторить попытку

### 🟡 Важные

2. **Добавить индексы**
   ```sql
   CREATE INDEX idx_results_user_id ON results(user_id);
   CREATE INDEX idx_results_date ON results(date);
   ```

3. **Добавить миграции БД**
   - Версионировать схему БД
   - Упростить обновления

4. **Добавить резервное копирование**
   - Регулярно копировать БД
   - Хранить на отдельном сервере

### 🟢 Желательные

5. **Добавить статистику по темам**
   - Отслеживать результаты по каждой теме
   - Показывать слабые области

6. **Добавить экспорт данных**
   - CSV/JSON экспорт результатов
   - Для анализа и отчетов

---

## 11. Заключение

### ✅ Сильные стороны:

- ✅ Правильное использование async/await
- ✅ Защита от SQL-инъекций
- ✅ Хорошее логирование
- ✅ Обработка ошибок в большинстве мест
- ✅ Изоляция данных по пользователям

### ⚠️ Области для улучшения:

- ⚠️ Обработка ошибок в `finish_quiz()`
- ⚠️ Отсутствие индексов
- ⚠️ Отсутствие миграций БД
- ⚠️ Отсутствие резервного копирования

### 📊 Общая оценка: **8/10**

Код хорошо структурирован и безопасен. Требуются небольшие улучшения для production-среды.
