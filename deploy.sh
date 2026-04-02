#!/bin/bash

# Скрипт для развертывания бота на удаленном сервере
# Использование: ./deploy.sh <server-ip> <bot-token>

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
    log_error "Использование: $0 <server-ip> <bot-token>"
    echo "Пример: $0 192.168.1.100 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
    exit 1
fi

SERVER_IP=$1
BOT_TOKEN=$2
SERVER_USER=${3:-root}
DEPLOY_DIR="/opt/finance-bot"

log_info "Начинаем развертывание бота на сервере $SERVER_IP"

# 1. Подключение к серверу и создание директории
log_info "Создаем директорию на сервере..."
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOY_DIR /data/finance-bot/{db,logs,data}"

# 2. Копирование файлов на сервер
log_info "Копируем файлы на сервер..."
scp -r \
    bot.py \
    questions.py \
    database.py \
    requirements.txt \
    Dockerfile \
    docker-compose.prod.yml \
    .dockerignore \
    .env.example \
    $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/

# 3. Создание .env файла на сервере
log_info "Создаем .env файл на сервере..."
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cat > $DEPLOY_DIR/.env << EOF
BOT_TOKEN=$BOT_TOKEN
EOF"

# 4. Запуск контейнера
log_info "Запускаем контейнер..."
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml up -d"

# 5. Проверка статуса
log_info "Проверяем статус контейнера..."
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml ps"

log_info "Просмотр логов (последние 20 строк)..."
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml logs --tail=20 finance-bot"

log_info "✅ Развертывание завершено!"
log_info "Бот запущен на сервере $SERVER_IP"
log_info "Для просмотра логов: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
log_info "Для остановки: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose -f docker-compose.prod.yml down'"
