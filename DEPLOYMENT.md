# 🚀 Руководство по развертыванию бота

Полное руководство по развертыванию Telegram-бота для проверки финансовой грамотности на удаленном сервере.

---

## 📋 Содержание

1. [Требования](#требования)
2. [Локальная разработка](#локальная-разработка)
3. [Docker локально](#docker-локально)
4. [Развертывание на сервере](#развертывание-на-сервере)
5. [Управление и мониторинг](#управление-и-мониторинг)
6. [Решение проблем](#решение-проблем)

---

## Требования

### Для локальной разработки
- Python 3.10+
- pip
- Токен Telegram бота

### Для Docker
- Docker 20.10+
- Docker Compose 2.0+ (или встроенный `docker compose`)

### Для удаленного сервера
- Linux сервер (Ubuntu 20.04+ или Debian 11+)
- SSH доступ
- Docker и Docker Compose установлены
- Минимум 512 MB RAM
- Минимум 1 GB свободного места на диске

---

## Локальная разработка

### 1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd <папка-проекта>
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# venv\Scripts\activate   # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Конфигурация

```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваш BOT_TOKEN
```

### 5. Запуск бота

```bash
python bot.py
```

Логи будут писаться в `logs/bot.log` и в консоль.

---

## Docker локально

### Быстрый старт

```bash
# 1. Создать .env файл
cp .env.example .env
# Отредактируйте .env

# 2. Запустить контейнер
docker-compose up -d

# 3. Проверить статус
docker-compose ps
docker-compose logs -f finance-bot

# 4. Остановить
docker-compose down
```

### Полезные команды

```bash
# Просмотр логов
docker-compose logs -f finance-bot

# Вход в контейнер
docker-compose exec finance-bot bash

# Перезагрузка
docker-compose restart

# Удаление контейнера и томов
docker-compose down -v
```

---

## Развертывание на сервере

### Способ 1: Автоматическое развертывание (рекомендуется)

#### Предварительные требования

- SSH доступ к серверу
- Docker установлен на сервере
- Ваш токен бота

#### Развертывание

```bash
# На локальной машине
chmod +x deploy.sh
./deploy.sh <server-ip> <bot-token> [username]

# Пример:
./deploy.sh 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ root
```

Скрипт автоматически:
- Создаст директории на сервере
- Скопирует все файлы
- Создаст `.env` файл
- Запустит контейнер
- Покажет статус

### Способ 2: Ручное развертывание

#### 1. Подключение к серверу

```bash
ssh user@your-server.com
```

#### 2. Установка Docker (если не установлен)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

#### 3. Клонирование репозитория

```bash
cd /opt
sudo git clone <url-репозитория> finance-bot
cd finance-bot
sudo chown -R $USER:$USER .
```

#### 4. Создание директорий для данных

```bash
mkdir -p /data/finance-bot/{db,logs,data}
```

#### 5. Конфигурация

```bash
cp .env.example .env
nano .env
# Добавьте BOT_TOKEN
```

#### 6. Запуск контейнера

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 7. Проверка статуса

```bash
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f finance-bot
```

---

## Управление и мониторинг

### П��осмотр логов

```bash
# Последние 100 строк
docker-compose -f docker-compose.prod.yml logs --tail=100 finance-bot

# В реальном времени
docker-compose -f docker-compose.prod.yml logs -f finance-bot

# Сохранить логи в файл
docker-compose -f docker-compose.prod.yml logs finance-bot > logs_backup.txt
```

### Проверка здоровья

```bash
# Статус контейнера
docker-compose -f docker-compose.prod.yml ps

# Детальная информация
docker inspect finance-bot-prod
```

### Перезагрузка

```bash
# Мягкая перезагрузка
docker-compose -f docker-compose.prod.yml restart

# Жесткая перезагрузка
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Обновление кода

```bash
# Остановить контейнер
docker-compose -f docker-compose.prod.yml down

# Обновить код
git pull origin main

# Пересобрать образ
docker-compose -f docker-compose.prod.yml build --no-cache

# Запустить
docker-compose -f docker-compose.prod.yml up -d
```

### Резервная копия данных

```bash
# Ск��пировать БД локально
scp user@server:/data/finance-bot/db/finance_bot.db ./backup_$(date +%Y%m%d).db

# Скопировать логи
scp -r user@server:/data/finance-bot/logs ./logs_backup_$(date +%Y%m%d)
```

---

## Решение проблем

### П��облема: "docker-compose: command not found"

**Решение:**
```bash
# Установить Docker Compose
sudo apt-get install docker-compose

# Или использовать встроенный docker compose
docker compose up -d  # вместо docker-compose up -d
```

### Проблема: Контейнер не запускается

**Проверка:**
```bash
# Просмотр логов ошибок
docker-compose logs finance-bot

# Проверка конфигурации
docker-compose config

# Проверка переменных окружения
docker-compose exec finance-bot env | grep BOT_TOKEN
```

### Проблема: Нет доступа к БД

**Решение:**
```bash
# Проверить права доступа
ls -la /data/finance-bot/db/

# Исправить права
sudo chown -R 1000:1000 /data/finance-bot/
```

### Проблема: Контейнер часто перезагружается

**Проверка:**
```bash
# Просмотр логов
docker-compose logs --tail=50 finance-bot

# Проверка ресурсов
docker stats finance-bot-prod

# Увеличить лимиты в docker-compose.prod.yml
```

### Проблема: Бот не отвечает на сообщения

**Проверка:**
```bash
# Проверить токен в .env
cat .env | grep BOT_TOKEN

# Проверить подключение к интернету
docker-compose exec finance-bot ping api.telegram.org

# Перезагрузить контейнер
docker-compose restart
```

### Проблема: Диск переполнен

**Решение:**
```bash
# Очистить старые логи
docker-compose logs --tail=0 finance-bot > /dev/null

# Удалить неиспользуемые образы
docker image prune -a

# Удалить неиспользуемые тома
docker volume prune
```

---

## Структура файлов на сервере

```
/opt/finance-bot/
├── bot.py
├── questions.py
├── database.py
├── requirements.txt
├── Dockerfile
├── docker-compose.prod.yml
├── .env
└── .dockerignore

/data/finance-bot/
├── db/
│   └── finance_bot.db
├── logs/
│   └── bot.log
└── data/
```

---

## Безопасность

### Рекомендации

1. **Защита токена**
   - Никогда не коммитьте `.env` в git
   - Используйте переменные окружения
   - Ограничьте доступ к файлу `.env`

2. **Обновления**
   - Регулярно обновляйте зависимости
   - Следите за обновлениями Docker
   - Проверяйте уязвимости

3. **Мониторинг**
   - Настройте логирование
   - Проверяйте логи на ошибки
   - Используйте healthcheck

4. **Резервные копии**
   - Регулярно делайте резервные копии БД
   - Сохраняйте логи
   - Тестируйте восстановление

---

## Поддержка

Если у вас возникли проблемы:

1. Проверьте логи: `docker-compose logs finance-bot`
2. Убедитесь, что токен правильный
3. Проверьте подключение к интернету
4. Перезагрузите контейнер
5. Обратитесь к документации Docker

---

## Дополнительные ресурсы

- [Docker документация](https://docs.docker.com/)
- [Docker Compose документация](https://docs.docker.com/compose/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot документация](https://python-telegram-bot.readthedocs.io/)
