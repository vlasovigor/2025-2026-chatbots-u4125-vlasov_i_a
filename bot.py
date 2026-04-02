"""
Telegram-бот для проверки финансовой грамотности.

Режимы работы:
  - Общий тест:       10 случайных вопросов из всех тем, результат в конце
  - Тематический тест: 5 вопросов по выбранной теме, результат в конце
  - Режим обучения:   вопросы с объяснением после каждого ответа

Зависимости: python-telegram-bot[job-queue], aiosqlite, python-dotenv
"""

from __future__ import annotations

import logging
import os
import random
from typing import Optional

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from database import get_user_results, get_user_stats, init_db, save_result
from questions import QUESTIONS, TOPICS

# ─── Загрузка переменных окружения ────────────────────────────────────────────
load_dotenv()
# Поддерживаем оба варианта имени переменной
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── Логирование ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Состояния ConversationHandler ────────────────────────────────────────────
# Главное меню
MAIN_MENU = 0
# Выбор темы для тематического теста
TOPIC_SELECT = 1
# Прохождение теста (вопрос-ответ)
IN_QUIZ = 2
# Просмотр результатов
RESULTS_VIEW = 3
# Подтверждение прерывания теста
CONFIRM_QUIT = 4

# ─── Константы ────────────────────────────────────────────────────────────────
GENERAL_QUIZ_SIZE = 10   # Вопросов в общем тесте
TOPIC_QUIZ_SIZE = 5      # Вопросов в тематическом тесте

# Уровни грамотности (процент правильных ответов)
LEVELS = [
    (0,  40,  "🔴 Низкий",    "Стоит уделить время изучению основ финансовой грамотности."),
    (40, 60,  "🟡 Базовый",   "Вы знаете основы, но есть пробелы — продолжайте учиться!"),
    (60, 80,  "🟢 Средний",   "Хороший результат! Подтяните слабые темы."),
    (80, 101, "🏆 Высокий",   "Отличный результат! Вы хорошо разбираетесь в финансах."),
]

# Эмодзи для вариантов ответа
OPTION_EMOJI = ["🅰", "🅱", "🅲", "🅳"]


# ─── Вспомогательные функции ───────────────────────────��──────────────────────

def get_level(score: int, total: int) -> tuple[str, str]:
    """Возвращает (название уровня, комментарий) по результату теста."""
    percent = score / total * 100 if total > 0 else 0
    for lo, hi, name, comment in LEVELS:
        if lo <= percent < hi:
            return name, comment
    return LEVELS[-1][2], LEVELS[-1][3]


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню."""
    keyboard = [
        [InlineKeyboardButton("📝 Пройти тест",       callback_data="menu_general")],
        [InlineKeyboardButton("📚 Выбрать тему",       callback_data="menu_topic")],
        [InlineKeyboardButton("🎓 Режим обучения",     callback_data="menu_learning")],
        [InlineKeyboardButton("📊 Мои результаты",     callback_data="menu_results")],
        [InlineKeyboardButton("❓ Помощь",             callback_data="menu_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_topic_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора темы."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"topic_{key}")]
        for key, label in TOPICS.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def build_answer_keyboard(question: dict, q_index: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами ответа.
    На кнопках — только буква (А/Б/В/Г), полный текст варианта — в сообщении.
    """
    labels = ["А", "Б", "В", "Г"]
    # Кнопки попарно в одну строку, чтобы не обрезались
    buttons = [
        InlineKeyboardButton(labels[i], callback_data=f"answer_{q_index}_{i}")
        for i in range(len(question["options"]))
    ]
    # Все 4 кнопки в одну строку
    keyboard = [buttons]
    return InlineKeyboardMarkup(keyboard)


def format_question_text(question: dict, num: int, total: int) -> str:
    """Форматирует текст вопроса с номером, темой и вариантами ответа."""
    topic_label = TOPICS.get(question["topic"], question["topic"])
    labels = ["А", "Б", "В", "Г"]
    options_text = "\n".join(
        f"  *{labels[i]}*. {opt}"
        for i, opt in enumerate(question["options"])
    )
    return (
        f"*Вопрос {num}/{total}* — {topic_label}\n\n"
        f"❓ {question['text']}\n\n"
        f"{options_text}"
    )


def format_result_message(
    score: int,
    total: int,
    wrong_answers: list[dict],
    topic_stats: dict[str, list[int]],
    mode: str,
) -> str:
    """
    Формирует итоговое сообщение с результатом, разбором ошибок
    и рекомендациями по слабым темам.
    """
    level_name, level_comment = get_level(score, total)
    percent = round(score / total * 100) if total > 0 else 0

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 *Результат теста*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Правильных ответов: *{score}/{total}* ({percent}%)",
        f"📈 Уровень: *{level_name}*",
        f"💬 {level_comment}",
        "",
    ]

    # Статистика по темам (только если тем больше одной)
    if len(topic_stats) > 1:
        lines.append("📊 *Статистика по темам:*")
        for topic_key, (correct, total_t) in topic_stats.items():
            topic_label = TOPICS.get(topic_key, topic_key)
            bar = "✅" * correct + "❌" * (total_t - correct)
            lines.append(f"  {topic_label}: {bar} {correct}/{total_t}")
        lines.append("")

    # Разбор ошибок
    if wrong_answers:
        lines.append("❌ *Разбор ошибок:*")
        for i, item in enumerate(wrong_answers, 1):
            q = item["question"]
            chosen = item["chosen"]
            correct_idx = q["correct"]
            lines.append(
                f"\n*{i}. {q['text']}*\n"
                f"  Ваш ответ: {OPTION_EMOJI[chosen]} {q['options'][chosen]}\n"
                f"  Правильно: {OPTION_EMOJI[correct_idx]} {q['options'][correct_idx]}\n"
                f"  💡 {q['explanation']}"
            )
        lines.append("")

    # Рекомендации по слабым темам
    weak_topics = [
        TOPICS.get(k, k)
        for k, (c, t) in topic_stats.items()
        if t > 0 and c / t < 0.6
    ]
    if weak_topics:
        lines.append("📚 *Рекомендуем подтянуть:*")
        for wt in weak_topics:
            lines.append(f"  • {wt}")

    return "\n".join(lines)


def init_quiz_state(
    context: ContextTypes.DEFAULT_TYPE,
    questions: list[dict],
    mode: str,
    topic: Optional[str] = None,
) -> None:
    """Инициализирует состояние текущего теста в context.user_data."""
    context.user_data["quiz"] = {
        "questions": questions,   # список вопросов
        "current": 0,             # индекс текущего вопроса
        "score": 0,               # количество правильных ответов
        "mode": mode,             # 'general', 'topic', 'learning'
        "topic": topic,           # ключ темы (для тематического теста)
        "wrong_answers": [],      # список ошибок для разбора
        "topic_stats": {},        # {topic_key: [correct, total]}
        "answered": False,        # флаг: пользователь уже ответил на текущий вопрос
        "all_answers": [],        # список всех ответов: {question, chosen, is_correct}
    }


def format_full_review(all_answers: list[dict]) -> list[str]:
    """
    Формирует список сообщений с полным разбором теста.
    Возвращает список строк (разбито на части, т.к. Telegram ограничивает длину сообщения).
    """
    labels = ["А", "Б", "В", "Г"]
    parts = []
    current_part = ["📋 *Полный ра��бор теста*\n"]

    for i, item in enumerate(all_answers, 1):
        q = item["question"]
        chosen = item["chosen"]
        correct_idx = q["correct"]
        is_correct = item["is_correct"]
        topic_label = TOPICS.get(q["topic"], q["topic"])

        icon = "✅" if is_correct else "❌"

        block_lines = [
            f"\n{icon} *Вопрос {i}* — {topic_label}",
            f"_{q['text']}_",
        ]

        # Все варианты ответа с пометками
        for j, opt in enumerate(q["options"]):
            if j == correct_idx and j == chosen:
                marker = "✅"  # пр��вильный и выбранный
            elif j == correct_idx:
                marker = "☑️"  # правильный, но не выбранный
            elif j == chosen:
                marker = "❌"  # выбранный, но неправильный
            else:
                marker = "▫️"  # не выбранный и неправильный
            block_lines.append(f"  {marker} *{labels[j]}*. {opt}")

        if not is_correct:
            block_lines.append(f"  💡 _{q['explanation']}_")

        block = "\n".join(block_lines)

        # Telegram ограничивает сообщение ~4096 символами — разбиваем на части
        if len("\n".join(current_part)) + len(block) > 3800:
            parts.append("\n".join(current_part))
            current_part = [block]
        else:
            current_part.append(block)

    if current_part:
        parts.append("\n".join(current_part))

    return parts


# ─── Обработчики команд ───────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start — показывает главное меню."""
    user = update.effective_user
    text = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Я бот для проверки *финансовой грамотности*.\n\n"
        "Выбери, что хочешь сделать:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(),
    )
    return MAIN_MENU


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /help."""
    text = (
        "📖 *Справка по боту*\n\n"
        "*Режимы тестирования:*\n"
        "📝 *Пройти тест* — 10 случайных вопросов из всех тем. "
        "Результат и разбор ошибок — в конце.\n\n"
        "📚 *Выбрать тему* — 5 вопросов по выбранной теме.\n\n"
        "🎓 *Режим обучения* — после каждого ответа бот объясняет, "
        "правильно ли вы ответили и почему.\n\n"
        "📊 *Мои результаты* — история ваших прохождений.\n\n"
        "*Команды:*\n"
        "/start — главное меню\n"
        "/results — мои результаты\n"
        "/help — эта справка"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=build_main_menu_keyboard())
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown",
                                                      reply_markup=build_main_menu_keyboard())
    return MAIN_MENU


async def cmd_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /results — показывает историю результатов."""
    await show_results(update, context)
    return MAIN_MENU


# ─── Обработчики кнопок главного меню ────────────────────────────────────────

async def menu_general(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает общий тест из 10 случайных вопросов."""
    query = update.callback_query
    await query.answer()

    # Выбираем случайные вопросы из всей базы
    questions = random.sample(QUESTIONS, min(GENERAL_QUIZ_SIZE, len(QUESTIONS)))
    init_quiz_state(context, questions, mode="general")

    await query.edit_message_text(
        "📝 *Общий тест*\n\n"
        f"Вас ждут *{len(questions)} вопросов* по всем темам.\n"
        "Результат и разбор ошибок — в конце.\n\n"
        "Поехали! 🚀",
        parse_mode="Markdown",
    )
    # Отправляем первый вопрос
    await send_question(update, context)
    return IN_QUIZ


async def menu_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню выбора темы."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 *Выбор темы*\n\nВыберите тему для тестирования:",
        parse_mode="Markdown",
        reply_markup=build_topic_keyboard(),
    )
    return TOPIC_SELECT


async def menu_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает режим обучения (10 вопросов с объяснениями)."""
    query = update.callback_query
    await query.answer()

    questions = random.sample(QUESTIONS, min(GENERAL_QUIZ_SIZE, len(QUESTIONS)))
    init_quiz_state(context, questions, mode="learning")

    await query.edit_message_text(
        "🎓 *Режим обучения*\n\n"
        f"Вас ждут *{len(questions)} вопросов*.\n"
        "После каждого ответа я объясню, правильно ли вы ответили и почему.\n\n"
        "Поехали! 🚀",
        parse_mode="Markdown",
    )
    await send_question(update, context)
    return IN_QUIZ


async def menu_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает историю результатов пользователя."""
    query = update.callback_query
    await query.answer()
    await show_results(update, context)
    return MAIN_MENU


async def menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает справку."""
    query = update.callback_query
    await query.answer()
    await cmd_help(update, context)
    return MAIN_MENU


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Главное меню:",
        reply_markup=build_main_menu_keyboard(),
    )
    return MAIN_MENU


# ─── Выбор темы ───────────────────────────────────────────────────────────────

async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает тематический тест по выбранной теме."""
    query = update.callback_query
    await query.answer()

    # Извлекаем ключ темы из callback_data вида "topic_budget"
    topic_key = query.data.split("_", 1)[1]
    topic_label = TOPICS.get(topic_key, topic_key)

    # Фильтруем вопросы по теме
    topic_questions = [q for q in QUESTIONS if q["topic"] == topic_key]
    if not topic_questions:
        await query.edit_message_text(
            "⚠️ По этой теме пока нет вопросов. Выберите другую.",
            reply_markup=build_topic_keyboard(),
        )
        return TOPIC_SELECT

    questions = random.sample(topic_questions, min(TOPIC_QUIZ_SIZE, len(topic_questions)))
    init_quiz_state(context, questions, mode="topic", topic=topic_key)

    await query.edit_message_text(
        f"📚 *Тема: {topic_label}*\n\n"
        f"Вас ждут *{len(questions)} вопросов* по этой теме.\n"
        "Результат и разбор ошибок — в конце.\n\n"
        "Поехали! 🚀",
        parse_mode="Markdown",
    )
    await send_question(update, context)
    return IN_QUIZ


# ─── Логика теста ─────────────────────────────────────────────────────────────

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет текущий вопрос теста."""
    quiz = context.user_data["quiz"]
    idx = quiz["current"]
    question = quiz["questions"][idx]
    total = len(quiz["questions"])

    text = format_question_text(question, idx + 1, total)
    
    # Добавляем кнопку прерывания теста
    buttons = list(build_answer_keyboard(question, idx).inline_keyboard[0])
    buttons.append(InlineKeyboardButton("⏹️ Прервать", callback_data="confirm_quit"))
    keyboard = InlineKeyboardMarkup([buttons])

    # Отправляем новое сообщение с вопросом
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    # Сохраняем message_id, чтобы потом редактировать
    quiz["last_message_id"] = msg.message_id


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ответ пользователя на вопрос.
    callback_data формат: "answer_{q_index}_{option_index}"
    """
    query = update.callback_query
    await query.answer()

    quiz = context.user_data.get("quiz")
    if not quiz:
        # Состояние потеряно — возвращаем в меню
        await query.edit_message_text(
            "⚠️ Сессия истекла. Начните заново.",
            reply_markup=build_main_menu_keyboard(),
        )
        return MAIN_MENU

    # Парсим callback_data
    parts = query.data.split("_")
    q_index = int(parts[1])
    chosen = int(parts[2])

    # Защита от повторного нажатия на уже отвеченный вопрос
    if quiz.get("answered"):
        return IN_QUIZ

    # Проверяем, что ответ относится к текущему вопросу
    if q_index != quiz["current"]:
        return IN_QUIZ

    quiz["answered"] = True
    question = quiz["questions"][q_index]
    correct = question["correct"]
    is_correct = chosen == correct

    # Обновляем счёт
    if is_correct:
        quiz["score"] += 1
    else:
        quiz["wrong_answers"].append({"question": question, "chosen": chosen})

    # Обновляем статистику по темам
    topic_key = question["topic"]
    if topic_key not in quiz["topic_stats"]:
        quiz["topic_stats"][topic_key] = [0, 0]
    quiz["topic_stats"][topic_key][1] += 1
    if is_correct:
        quiz["topic_stats"][topic_key][0] += 1

    # Сохраняем ответ пользователя для полного разбора
    quiz["all_answers"].append({
        "question": question,
        "chosen": chosen,
        "is_correct": is_correct,
    })

    # ── Режим обучения: показываем объяснение после каждого ответа ──
    if quiz["mode"] == "learning":
        if is_correct:
            feedback = f"✅ *Правильно!*\n\n💡 {question['explanation']}"
        else:
            feedback = (
                f"❌ *Неверно.*\n\n"
                f"Правильный ответ: {OPTION_EMOJI[correct]} *{question['options'][correct]}*\n\n"
                f"💡 {question['explanation']}"
            )

        # Редактируем сообщение с вопросом — убираем кнопки, добавляем объяснение
        await query.edit_message_text(
            f"{format_question_text(question, q_index + 1, len(quiz['questions']))}\n\n"
            f"{feedback}",
            parse_mode="Markdown",
        )

        # Кнопка «Следующий вопрос» или «Завершить»
        is_last = q_index + 1 >= len(quiz["questions"])
        btn_text = "📊 Посмотреть результат" if is_last else "➡️ Следующий вопрос"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Нажмите, чтобы продолжить:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn_text, callback_data="next_question")]]
            ),
        )
        return IN_QUIZ

    # ── Обычный режим: сразу переходим к следующему вопросу ──
    await advance_quiz(update, context, query)
    return IN_QUIZ


async def next_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки 'Следующий вопрос' в режиме обучения."""
    query = update.callback_query
    await query.answer()
    # Удаляем кнопку «Следующий вопрос»
    await query.delete_message()
    await advance_quiz(update, context, query)
    return IN_QUIZ


async def advance_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    """Переходит к следующему вопросу или завершает тест."""
    quiz = context.user_data["quiz"]
    quiz["current"] += 1
    quiz["answered"] = False

    if quiz["current"] >= len(quiz["questions"]):
        # Тест завершён
        await finish_quiz(update, context)
    else:
        # Следующий вопрос
        await send_question(update, context)


async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершает тест: сохраняет результат и показывает итоговое сообщение."""
    quiz = context.user_data["quiz"]
    user = update.effective_user

    score = quiz["score"]
    total = len(quiz["questions"])
    mode = quiz["mode"]
    topic = quiz.get("topic")
    wrong_answers = quiz["wrong_answers"]
    topic_stats = quiz["topic_stats"]

    # Сохраняем результат в БД
    try:
        await save_result(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            mode=mode,
            topic=topic,
            score=score,
            total=total,
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения результата: {e}")

    # Формируем итоговое сообщение
    result_text = format_result_message(score, total, wrong_answers, topic_stats, mode)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=result_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Все вопросы и ответы", callback_data="show_review")],
            [InlineKeyboardButton("� Пройти ещё раз", callback_data="menu_general")],
            [InlineKeyboardButton("📚 Выбрать тему",   callback_data="menu_topic")],
            [InlineKeyboardButton("🏠 Главное меню",   callback_data="back_main")],
        ]),
    )

    # Сохраняем all_answers для просмотра позже
    context.user_data["last_quiz_answers"] = quiz["all_answers"]

    # Очищаем состояние теста
    context.user_data.pop("quiz", None)


async def show_full_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает полный разбор всех вопросов и ответов."""
    query = update.callback_query
    await query.answer()

    all_answers = context.user_data.get("last_quiz_answers", [])
    if not all_answers:
        await query.edit_message_text(
            "⚠️ Данные о тесте не найдены.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
            ]),
        )
        return MAIN_MENU

    # Формируем части разбора
    parts = format_full_review(all_answers)

    # Отправляем каждую часть отдельным сообщением
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        if is_last:
            # На последней части добавляем кнопки меню
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=part,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="menu_general")],
                    [InlineKeyboardButton("🏠 Главное меню",   callback_data="back_main")],
                ]),
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=part,
                parse_mode="Markdown",
            )

    return MAIN_MENU


# ─── Просмотр результатов ─────────────────────────────────────────────────────

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю результатов и общую статистику пользователя."""
    user = update.effective_user

    try:
        results = await get_user_results(user.id, limit=10)
        stats = await get_user_stats(user.id)
    except Exception as e:
        logger.error(f"Ошибка получения результатов: {e}")
        results, stats = [], {}

    if not results:
        text = (
            "📊 *Мои результаты*\n\n"
            "У вас пока нет пройденных тестов.\n"
            "Нажмите «Пройти тест», чтобы начать!"
        )
    else:
        mode_labels = {
            "general":  "📝 Общий тест",
            "topic":    "📚 По теме",
            "learning": "🎓 Обучение",
        }

        lines = ["📊 *Мои результаты*\n"]

        # Общая статистика
        if stats:
            avg = stats["avg_percent"]
            lines += [
                f"Всего тестов: *{stats['total_tests']}*",
                f"Правильных ответов: *{stats['total_correct']}/{stats['total_questions']}*",
                f"Средний результат: *{avg}%*",
                "",
                "📋 *Последние 10 попыток:*",
            ]

        # История попыток
        for r in results:
            mode_label = mode_labels.get(r["mode"], r["mode"])
            topic_label = f" — {TOPICS.get(r['topic'], r['topic'])}" if r["topic"] else ""
            percent = round(r["score"] / r["total"] * 100) if r["total"] > 0 else 0
            level_name, _ = get_level(r["score"], r["total"])
            lines.append(
                f"• {r['date']} | {mode_label}{topic_label}\n"
                f"  {r['score']}/{r['total']} ({percent}%) — {level_name}"
            )

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
    ])

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )


# ─── Прерывание теста ─────────────────────────────────────────────────────────

async def confirm_quit_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает подтверждение прерывания теста."""
    query = update.callback_query
    await query.answer()

    quiz = context.user_data.get("quiz")
    if not quiz:
        return MAIN_MENU

    current = quiz["current"] + 1
    total = len(quiz["questions"])

    await query.edit_message_text(
        f"⚠️ *Вы уверены?*\n\n"
        f"Вы прошли {current}/{total} вопросов.\n"
        f"Текущий результат: {quiz['score']} правильных ответов.\n\n"
        f"Если вы прервёте тест, результат не будет сохранён.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, прервать", callback_data="quit_confirmed")],
            [InlineKeyboardButton("❌ Нет, продолжить", callback_data="quit_cancelled")],
        ]),
    )
    return CONFIRM_QUIT


async def quit_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение прерывания теста."""
    query = update.callback_query
    await query.answer()

    # Очищаем состояние теста
    context.user_data.pop("quiz", None)

    await query.edit_message_text(
        "❌ Тест прерван.\n\n"
        "Результат не был сохранён.",
        reply_markup=build_main_menu_keyboard(),
    )
    return MAIN_MENU


async def quit_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена прерывания теста."""
    query = update.callback_query
    await query.answer()

    quiz = context.user_data.get("quiz")
    if not quiz:
        await query.edit_message_text(
            "⚠️ Сессия истекла.",
            reply_markup=build_main_menu_keyboard(),
        )
        return MAIN_MENU

    # Возвращаемся к текущему во��росу
    idx = quiz["current"]
    question = quiz["questions"][idx]
    total = len(quiz["questions"])

    text = format_question_text(question, idx + 1, total)
    buttons = list(build_answer_keyboard(question, idx).inline_keyboard[0])
    buttons.append(InlineKeyboardButton("⏹️ Прервать", callback_data="confirm_quit"))
    keyboard = InlineKeyboardMarkup([buttons])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return IN_QUIZ


# ─── Обработчик неизвестных callback ─────────────────────────────────────────

async def unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает неизвестные callback-запросы."""
    await update.callback_query.answer("⚠️ Неизвестная команда")


# ─── Запуск бота ──────────────────────────────────────────────────────────────

def main() -> None:
    """Точка входа: инициализация БД и запуск бота."""
    if not BOT_TOKEN:
        raise ValueError(
            "Токен бота не найден! Укажите BOT_TOKEN в файле .env"
        )

    # Инициализируем базу данных (создаём таблицы, если их нет)
    import asyncio
    asyncio.get_event_loop().run_until_complete(init_db())
    logger.info("База данных инициализирована")

    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # ── ConversationHandler — основной сценарий ──
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(menu_general,  pattern="^menu_general$"),
                CallbackQueryHandler(menu_topic,    pattern="^menu_topic$"),
                CallbackQueryHandler(menu_learning, pattern="^menu_learning$"),
                CallbackQueryHandler(menu_results,  pattern="^menu_results$"),
                CallbackQueryHandler(menu_help,     pattern="^menu_help$"),
                CallbackQueryHandler(back_main,     pattern="^back_main$"),
            ],
            TOPIC_SELECT: [
                CallbackQueryHandler(topic_selected, pattern="^topic_"),
                CallbackQueryHandler(back_main,      pattern="^back_main$"),
            ],
            IN_QUIZ: [
                CallbackQueryHandler(handle_answer,        pattern="^answer_"),
                CallbackQueryHandler(next_question_callback, pattern="^next_question$"),
                CallbackQueryHandler(show_full_review,     pattern="^show_review$"),
                CallbackQueryHandler(confirm_quit_quiz,    pattern="^confirm_quit$"),
                # Кнопки «ещё раз» и «меню» доступны после завершения теста
                CallbackQueryHandler(menu_general,  pattern="^menu_general$"),
                CallbackQueryHandler(menu_topic,    pattern="^menu_topic$"),
                CallbackQueryHandler(back_main,     pattern="^back_main$"),
            ],
            CONFIRM_QUIT: [
                CallbackQueryHandler(quit_confirmed, pattern="^quit_confirmed$"),
                CallbackQueryHandler(quit_cancelled, pattern="^quit_cancelled$"),
            ],
            RESULTS_VIEW: [
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[
            CommandHandler("start",   cmd_start),
            CommandHandler("help",    cmd_help),
            CommandHandler("results", cmd_results),
        ],
        # Разрешаем повторный вход (например, /start во время теста)
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    # Отдельные команды вне ConversationHandler
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("results", cmd_results))

    # Обработчик неизвестных callback
    app.add_handler(CallbackQueryHandler(unknown_callback))

    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
