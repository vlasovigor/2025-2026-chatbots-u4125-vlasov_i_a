# 🤖 Бот по финансовой грамотности

Telegram-бот для проверки и повышения уровня финансовой грамотности. Бот задаёт вопросы по 8 темам, считает баллы, объясняет ошибки и даёт рекомендации.

Ссылка на бота: [клик](https://t.me/friend_accountant_bot)
---

## 📋 Функционал

### Режимы тестирования

| Режим | Описание |
|---|---|
| 📝 **Пройти тест** | 10 случайных вопросов из всех тем. Результат и разбор ошибок — в конце |
| 📚 **Выбрать тему** | 5 вопросов по выбранной теме |
| 🎓 **Режим обучения** | После каждого ответа — объяснение правильного ответа |
| 📊 **Мои результаты** | История прохождений и общая статистика |

### Темы вопросов

- 💰 Бюджет
- 💳 Кредиты
- 🏦 Вклады
- 📈 Инфляция
- 🧾 Налоги
- 📊 Инвестиции
- 🚨 Мошенничество
- 🔒 Финансовая безопасность

### Уровни грамотности

| Результат | Уровень |
|---|---|
| 0–39% | 🔴 Низкий |
| 40–59% | 🟡 Базовый |
| 60–79% | 🟢 Средний |
| 80–100% | 🏆 Высокий |

### Итогов��й отчёт включает

- Количество правильных ответов и процент
- Уровень финансовой грамотности
- Статистику по каждой теме
- Разбор ошибок с объяснениями
- Рекомендации по слабым темам

---

## 🗂 Структура проекта

```
.
├── bot.py           # Основной код бота (обработчики, логика теста)
├── questions.py     # База вопросов (28 вопросов по 8 темам)
├── database.py      # Работа с SQLite (сохранение и чтение результатов)
├── requirements.txt # Зависимости Python
├── .env.example     # Пример файла конфигурации
├── .env             # Ваш файл с токеном (создать самостоятельно)
└── finance_bot.db   # База данных SQLite (создаётся автоматически)
```

---

## 🚀 Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone <url-репозитория>
cd <папка-проекта>
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Получить токен бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и скопируйте полученный токен

### 5. Создать файл `.env`

```bash
cp .env.example .env
```

Откройте `.env` и вставьте ваш токен:

```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### 6. Запустить бота

```bash
python bot.py
```

---

## 🐳 Docker (запуск на удаленном сервере)

### Требования

- Docker 20.10+
- Docker Compose 2.0+ (или `docker compose` ��строенный в Docker Desktop)

### Установка Docker и Docker Compose

#### macOS

```bash
# Установить Docker Desktop (включает Docker и Docker Compose)
brew install --cask docker

# Или скачать с https://www.docker.com/products/docker-desktop
```

#### Linux (Ubuntu/Debian)

```bash
# Установить Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Добавить текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Windows

Скачайте [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop)

### Проверка установки

```bash
docker --version
docker compose version
# или
docker-compose --version
```

### Быстрый старт с Docker Compose

#### 1. Создать файл `.env`

```bash
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваш токен:

```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

#### 2. Запустить бота

```bash
docker-compose up -d
```

#### 3. Проверить статус

```bash
docker-compose ps
docker-compose logs -f finance-bot
```

#### 4. Остановить бота

```bash
docker-compose down
```

### Сборка и запуск вручную

#### Сборка образа

```bash
docker build -t finance-bot:latest .
```

#### Запуск контейнера

```bash
docker run -d \
  --name finance-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=<ваш-токен> \
  -v $(pwd)/finance_bot.db:/app/finance_bot.db \
  -v $(pwd)/logs:/app/logs \
  finance-bot:latest
```

#### Просмотр логов

```bash
docker logs -f finance-bot
```

#### Остановка контейнера

```bash
docker stop finance-bot
docker rm finance-bot
```

### Развертывание на удаленном сервере

#### Способ 1: Автоматическое развертывание (рекомендуется)

Используйте скрипт `deploy.sh` для автоматического развертывания:

```bash
# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запустить развертывание
./deploy.sh <server-ip> <bot-token> [username]

# Пример:
./deploy.sh 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ root
```

Скрипт автоматически:
- Создаст необходимые директории на сервере
- Скопирует все файлы проекта
- Создаст `.env` файл с токеном
- Запустит контейнер в продакшене
- Покажет статус и логи

#### Способ 2: Ручное развертывание

##### 1. Подключиться к серверу

```bash
ssh user@your-server.com
```

##### 2. Клонировать репозиторий

```bash
git clone <url-репозитория>
cd <папка-проекта>
```

##### 3. Создать `.env` файл

```bash
nano .env
```

Добавьте:

```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

##### 4. Запустить с Docker Compose (продакшн конфигурация)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

##### 5. Проверить статус

```bash
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f finance-bot
```

### Конфигурации Docker Compose

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | Локальная разработка |
| `docker-compose.prod.yml` | Продакшн на удаленном сервере |

**Различия:**
- `prod` версия использует `restart: always` (всегда перезагружать)
- Более строгие ограничения ресурсов
- Более частые проверки здоровья
- Больший размер логов (50 MB вместо 10 MB)
- Пути к томам на хосте: `/data/finance-bot/`

### Полезные команды

| Команда | Описание |
|---|---|
| `docker-compose up -d` | Запустить в фоне |
| `docker-compose down` | Остановить и удалить контейнеры |
| `docker-compose logs -f` | Просмотр логов в реальном времени |
| `docker-compose restart` | Перезагрузить контейнер |
| `docker-compose exec finance-bot bash` | Войти в контейнер |
| `docker ps` | Список запущенных контейнеров |
| `docker images` | Список образов |

### Структура томов

```
.
├── finance_bot.db    # База данных (сохраняется между перезагрузками)
├── logs/             # Логи приложения
└── data/             # Дополнительные данные
```

### Переменные окружения в Docker

| Переменная | Значение | Описание |
|---|---|---|
| `BOT_TOKEN` | `<ваш-токен>` | Токен бота (обязательно) |
| `PYTHONUNBUFFERED` | `1` | Вывод логов в реальном времени |

### Проверка здоровья контейнера

Docker Compose автоматически проверяет здоровье контейнера каждые 30 секунд. Если контейнер не отвечает, он будет перезагружен.

```bash
docker-compose ps
# STATUS: Up X seconds (healthy)
```

---

## ⚙️ Конфигурация

Все настройки хранятся в файле `.env`:

| Переменная | Описание | Обязательная |
|---|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather | ✅ Да |

---

## 🛠 Технологии

| Библиотека | Версия | Назначение |
|---|---|---|
| `python-telegram-bot` | 21.9 | Работа с Telegram Bot API (async) |
| `aiosqlite` | 0.20.0 | Асинхронная работа с SQLite |
| `python-dotenv` | 1.0.1 | Загрузка переменн��х окружения из `.env` |

---

## 💾 База данных

Результаты сохраняются в файл `finance_bot.db` (SQLite). Таблица `results`:

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER | Первичный ключ |
| `user_id` | INTEGER | Telegram ID пользователя |
| `username` | TEXT | @username пользователя |
| `first_name` | TEXT | Имя пользователя |
| `mode` | TEXT | Режим: `general`, `topic`, `learning` |
| `topic` | TEXT | Ключ темы (для тематического теста) |
| `score` | INTEGER | Количеств�� правильных ответов |
| `total` | INTEGER | Всего вопросов |
| `date` | TEXT | Дата и время прохождения |

---

## 📝 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Главное меню |
| `/results` | Мои результаты |
| `/help` | Справка |

---

## 🔧 Требования

- Python 3.10+
- Доступ к интернету для работы с Telegram API
