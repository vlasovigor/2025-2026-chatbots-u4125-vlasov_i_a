"""
Модуль для работы с базой данных SQLite.
Хранит результаты прохождения тестов пользователями.
"""

from __future__ import annotations

import aiosqlite
import os
from datetime import datetime

# Путь к файлу базы данных
DB_PATH = os.path.join(os.path.dirname(__file__), "finance_bot.db")


async def init_db() -> None:
    """Инициализация базы данных: создание таблиц при первом запуске."""
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
    Сохраняет результат прохождения теста.

    :param user_id:    Telegram ID пользователя
    :param username:   @username (может отсутствовать)
    :param first_name: Имя пользователя
    :param mode:       Режим теста: 'general', 'topic', 'learning'
    :param topic:      Ключ темы (только для тематического теста)
    :param score:      Количество правильных ответов
    :param total:      Всего вопросов
    """
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO results (user_id, username, first_name, mode, topic, score, total, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, first_name, mode, topic, score, total, date_str),
        )
        await db.commit()


async def get_user_results(user_id: int, limit: int = 10) -> list[dict]:
    """
    Возвращает последние результаты пользователя.

    :param user_id: Telegram ID пользователя
    :param limit:   Максимальное количество записей
    :return:        Список словарей с результатами
    """
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
            return [dict(row) for row in rows]


async def get_user_stats(user_id: int) -> dict:
    """
    Возвращает агрегированную статистику пользователя.

    :param user_id: Telegram ID пользователя
    :return:        Словарь со статистикой
    """
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
                return {}
            return {
                "total_tests": row[0],
                "total_correct": row[1],
                "total_questions": row[2],
                "avg_percent": row[3],
            }
