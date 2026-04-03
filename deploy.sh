#!/bin/bash

# Скрипт для развертывания бота на удаленном сервере
# Использование: ./deploy.sh <server-ip> <bot-token> [username] [ssh-key]
#
# Примеры:
#   ./deploy.sh 192.168.1.100 YOUR_BOT_TOKEN root
#   ./deploy.sh 192.168.1.100 YOUR_BOT_TOKEN ubuntu ~/.ssh/id_rsa

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    log_error "Использование: $0 <server-ip> <bot-token> [username] [ssh-key]"
    echo ""
    echo "Примеры:"
    echo "  $0 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
    echo "  $0 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ ubuntu"
    echo "  $0 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ ubuntu ~/.ssh/id_rsa"
    exit 1
fi

SERVER_IP=$1
BOT_TOKEN=$2
SERVER_USER=${3:-root}
SSH_KEY=${4:-}
DEPLOY_DIR="/opt/finance-bot"

# Формируем SSH опции
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
SCP_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"

if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
    SCP_OPTS="$SCP_OPTS -i $SSH_KEY"
fi

log_info "Начинаем развертывание бота на сервере $SERVER_IP"
log_info "Пользователь: $SERVER_USER"

# 1. Проверка подключения
log_info "Проверяем подключение к серверу..."
if ! ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "echo 'OK'" > /dev/null 2>&1; then
    log_error "Не удается подключиться к серверу $SERVER_IP"
    log_error "Проверьте:"
    log_error "  - IP адрес сервера"
    log_error "  - Имя пользователя"
    log_error "  - SSH ключ (если используется)"
    exit 1
fi

# 2. Создание директорий на сервере
log_info "Создаем директории на сервере..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOY_DIR /data/finance-bot/{db,logs,data}"

# 3. Копирование файлов на сервер
log_info "Копируем файлы на сервер..."
scp $SCP_OPTS \
    bot.py \
    questions.py \
    database.py \
    requirements.txt \
    Dockerfile \
    docker-compose.prod.yml \
    .dockerignore \
    .env.example \
    $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/

# 4. Создание .env файла на сервере
log_info "Создаем .env файл на сервере..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cat > $DEPLOY_DIR/.env << 'ENVEOF'
BOT_TOKEN=$BOT_TOKEN
ENVEOF"

# 5. Проверка и установка Docker на сервере
log_info "Проверяем Docker на сервере..."
if ! ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "which docker" > /dev/null 2>&1; then
    log_error "Docker не установлен на сервере!"
    exit 1
fi

# 5a. Проверка Docker Compose
log_info "Проверяем Docker Compose на сервере..."
if ! ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "which docker-compose > /dev/null 2>&1"; then
    log_warn "docker-compose не найден, устанавливаем..."
    ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "sudo apt-get update && sudo apt-get install -y docker-compose" || {
        log_error "Не удалось установить docker-compose"
        exit 1
    }
fi
log_info "docker-compose готов"

# 6. Запуск контейнера
log_info "Запускаем контейнер..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml up -d" || {
    log_error "Ошибка при запуске контейнера"
    exit 1
}

# 7. Проверка статуса
log_info "Проверяем статус контейнера..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml ps"

# 8. Просмотр логов
log_info "Просмотр логов (последние 20 строк)..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml logs --tail=20 finance-bot"

log_info "✅ Развертывание завершено!"
log_info "Бот запущен на сервере $SERVER_IP"
log_info ""
log_info "Полезные команды:"
log_info "  Просмотр логов: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
log_info "  Остановка: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml down'"
log_info "  Перезагрузка: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml restart'"
