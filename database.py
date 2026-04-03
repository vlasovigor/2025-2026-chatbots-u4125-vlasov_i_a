"""
Модуль для работы с базой данных SQLite.
Хранит результаты прохождения тестов пользователями.
"""

from __future__ import annotations

import aiosqlite
import logging
import os
from datetime import datetime

# Логирование
logger = logging.getLogger(__name__)

# Путь к файлу базы данных
# Используем переменную окружения DATA_DIR, если она установлена (��ля Docker)
# Иначе используем текущую директорию (для локальной разработки)
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DATA_DIR, "finance_bot.db")


async def init_db() -> None:
    """Инициализация базы данных: создание таблиц при первом запуске."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
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
            """)
            await db.commit()
        logger.info(f"✅ База данных инициализирована: {DB_PATH}")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}", exc_info=True)
        raise


async def save_result(
    user_id: int,
    username: str | None,
    first_name: str | None,
    mode: str,
    topic: str | None,
    score: int,
    total: int,
) -> None:
    """
    Сохраняет результат прохождения тест��.

    :param user_id:    Telegram ID пользователя
    :param username:   @username (может отсутствовать)
    :param first_name: Имя пользователя
    :param mode:       Режим теста: 'general', 'topic', 'learning'
    :param topic:      Ключ темы (только для тематического теста)
    :param score:      Количество правильных ответов
    :param total:      Всего вопросов
    """
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


async def get_user_results(user_id: int, limit: int = 10) -> list[dict]:
    """
    Возвращает последние результаты пользователя.

    :param user_id: Telegram ID пользователя
    :param limit:   Максимальное количество записей
    :return:        Список словарей с результатами
    """
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


async def get_user_stats(user_id: int) -> dict:
    """
    Возвращает агрегированную статистику пользователя.

    :param user_id: Telegram ID пользователя
    :return:        Словарь со статистикой
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Общее количество тестов и средний результат
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
