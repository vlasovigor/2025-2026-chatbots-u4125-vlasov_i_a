# 📦 Руководство по обновлению бота

## Быстрый старт

### Обновить на сервере по умолчанию (root@192.168.1.100)

```bash
cd /Users/igor/Downloads/education/vibecoding/2025-2026-chatbots-u4125-vlasov_i_a
./update.sh
```

### Обновить на конкретном сервере

```bash
./update.sh user@your-server.com
```

---

## Что делает скрипт

1. ✅ **Проверка окружения**
   - Проверяет наличие всех необходимых файлов локально
   - Проверяет SSH доступ к серверу

2. ✅ **Создание резервной копии**
   - Сохраняет текущую версию бота на сервере
   - Путь: `/data/finance-bot/backups/backup_YYYYMMDD_HHMMSS`

3. ✅ **Копирование файлов**
   - Копирует обновленные файлы на сервер:
     - `bot.py`
     - `database.py`
     - `docker-compose.prod.yml`
     - `questions.py`
     - `requirements.txt`
     - `Dockerfile`

4. ✅ **Остановка контейнера**
   - Останавливает текущий контейнер бота

5. ✅ **Очистка БД (опционально)**
   - Спрашивает, нужно ли удалить старую БД
   - Если ответить "y" - создается новая БД с нуля
   - Если ответить "n" - сохраняются все данные пользователей

6. ✅ **Пересборка и запуск**
   - Пересобирает Docker образ
   - Запускает контейнер с новыми файлами

7. ✅ **Проверка статуса**
   - Проверяет, что контейнер запущен
   - Показывает последние 20 строк логов

---

## Примеры использования

### Обновить код без очистки БД

```bash
./update.sh
# Ответить "n" на вопрос об удалении БД
```

**Результат:** Все данные пользователей сохранятся, обновится только код

### Обновить код и очистить БД

```bash
./update.sh
# Ответить "y" на вопрос об удалении БД
```

**Результат:** БД будет пересоздана, все данные пользователей удалятся

### Обновить на другом сервере

```bash
./update.sh admin@production.example.com
```

---

## Что обновляется

### Критические изменения (требуют пересборки)

- ✅ `bot.py` - основной код бота
- ✅ `database.py` - работа с БД
- ✅ `questions.py` - вопросы и темы
- ✅ `requirements.txt` - зависимости
- ✅ `Dockerfile` - конфигурация контейнера
- ✅ `docker-compose.prod.yml` - конфигурация Docker Compose

---

## Откат на предыдущую версию

Если что-то пошло не так, можно откатиться на предыдущую версию:

```bash
# Найти последнюю резервную копию
ssh root@192.168.1.100 "ls -la /data/finance-bot/backups/"

# Откатиться на конкретную версию
ssh root@192.168.1.100 "
  rm -rf /opt/finance-bot && \
  cp -r /data/finance-bot/backups/backup_20260403_153647 /opt/finance-bot && \
  cd /opt/finance-bot && \
  docker-compose -f docker-compose.prod.yml up -d
"
```

---

## Просмотр логов после обновления

### Просмотр последних 50 строк

```bash
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml logs --tail=50"
```

### Просмотр логов в реальном времени

```bash
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml logs -f"
```

### Просмотр логов файла

```bash
ssh root@192.168.1.100 "tail -100 /data/finance-bot/logs/bot.log"
```

---

## Проверка статуса контейнера

```bash
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml ps"
```

Должно вывести:
```
NAME                COMMAND             STATUS
finance-bot-prod    python bot.py       Up X minutes
```

---

## Проверка БД

### Скачать БД на локальный компьютер

```bash
scp root@192.168.1.100:/data/finance-bot/db/finance_bot.db ./finance_bot.db
```

### Посмотреть таблицы

```bash
sqlite3 finance_bot.db ".tables"
```

### Посмотреть результаты пользователей

```bash
sqlite3 finance_bot.db ".mode column" "SELECT * FROM results LIMIT 10;"
```

---

## Решение проблем

### Проблема: "SSH доступ не работает"

**Решение:**
```bash
# Проверить SSH ключ
ssh -v root@192.168.1.100 "echo OK"

# Если ключ не работает, используйте пароль
ssh root@192.168.1.100 "echo OK"
```

### Проблема: "Контейнер не запускается"

**Решение:**
```bash
# Посмотреть логи ошибок
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml logs --tail=100"

# Перезагрузить контейнер
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml restart"
```

### Проблема: "БД не создается"

**Решение:**
```bash
# Проверить директорию БД
ssh root@192.168.1.100 "ls -la /data/finance-bot/db/"

# Создать директорию если её нет
ssh root@192.168.1.100 "mkdir -p /data/finance-bot/db && chmod 777 /data/finance-bot/db"

# Перезагрузить контейнер
ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml restart"
```

---

## Автоматизация обновлений

### Создать cron задачу для еженедельного обновления

```bash
# Отредактировать crontab
crontab -e

# Добавить строку (обновление каждый понедельник в 2:00 AM)
0 2 * * 1 cd /Users/igor/Downloads/education/vibecoding/2025-2026-chatbots-u4125-vlasov_i_a && ./update.sh >> /tmp/bot_update.log 2>&1
```

---

## Мониторинг после обновления

### Проверить что бот отвечает

```bash
# Отправить /start команду боту в Telegram
# Бот должен ответить с главным меню
```

### Проверить что БД работает

```bash
# Пройти тест в боте
# Результат должен сохраниться в БД

# Проверить результат
scp root@192.168.1.100:/data/finance-bot/db/finance_bot.db ./finance_bot.db
sqlite3 finance_bot.db "SELECT * FROM results ORDER BY id DESC LIMIT 1;"
```

---

## Часто задаваемые вопросы

**Q: Потеряются ли данные пользователей при обновлении?**

A: Нет, если вы ответите "n" на вопрос об удалении БД. Все данные сохранятся.

**Q: Сколько времени занимает обновление?**

A: Обычно 2-3 минуты (зависит от скорости интернета и сервера).

**Q: Можно ли обновлять во время работы бота?**

A: Нет, скрипт остановит контейнер. Лучше обновлять в ночное время.

**Q: Что если обновление прерывается?**

A: Откатитесь на предыдущую версию используя команду из раздела "Откат на предыдущую версию".

---

## Поддержка

Если у вас возникли проблемы:

1. Посмотрите логи: `ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml logs --tail=100"`
2. Проверьте статус: `ssh root@192.168.1.100 "cd /opt/finance-bot && docker-compose -f docker-compose.prod.yml ps"`
3. Откатитесь на предыдущую версию если нужно
4. Свяжитесь с администратором
