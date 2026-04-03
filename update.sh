#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# Скрипт для обновления файлов бота на сервере
# 
# Использование:
#   ./update.sh                    # Обновить на сервере по умолчанию
#   ./update.sh root@192.168.1.100 # Обновить на конкретном сервере
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # Выход при ошибке

# ─── Конфигурация ─────────────────────────────────────────────────────────────

# Сервер по умолчанию
SERVER="${1:-root@192.168.1.100}"
REMOTE_PATH="/opt/finance-bot"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Функции ──────────────────────────────────────────────────────────────────

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ─── Проверки ─────────────────────────────────────────────────────────────────

print_header "Проверка окружения"

# Проверяем наличие необходимых файлов
FILES_TO_UPDATE=(
    "bot.py"
    "database.py"
    "docker-compose.prod.yml"
    "questions.py"
    "requirements.txt"
    "Dockerfile"
)

for file in "${FILES_TO_UPDATE[@]}"; do
    if [ ! -f "$LOCAL_PATH/$file" ]; then
        print_error "Файл не найден: $LOCAL_PATH/$file"
        exit 1
    fi
done

print_success "Все файлы найдены локально"

# Проверяем SSH доступ
print_info "Проверка SSH доступа к $SERVER..."
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'SSH OK'" > /dev/null 2>&1; then
    print_error "Не удается подключиться к серверу $SERVER"
    exit 1
fi

print_success "SSH доступ работает"

# ─── Резервная копия ──────────────────────────────────────────────────────────

print_header "Создание резервной копии"

BACKUP_DIR="/data/finance-bot/backups"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_$BACKUP_DATE"

print_info "Создаем резервную копию на сервере..."
ssh "$SERVER" "mkdir -p $BACKUP_DIR && \
    cp -r $REMOTE_PATH $BACKUP_DIR/$BACKUP_NAME && \
    echo 'Резервная копия создана: $BACKUP_DIR/$BACKUP_NAME'"

print_success "Резервная копия создана"

# ─── Копирование файлов ───────────────────────────────────────────────────────

print_header "Копирование файлов на сервер"

for file in "${FILES_TO_UPDATE[@]}"; do
    print_info "Копирую $file..."
    scp "$LOCAL_PATH/$file" "$SERVER:$REMOTE_PATH/" > /dev/null 2>&1
    print_success "$file скопирован"
done

# ─── Остановка контейнера ─────────────────────────────────────────────────────

print_header "Остановка контейнера"

print_info "Останавливаю контейнер..."
ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml down" > /dev/null 2>&1
print_success "Контейнер остановлен"

# ─── Удаление старой БД (опционально) ──────────────────────────────────────────

print_header "Очистка БД"

read -p "Удалить старую БД и создать новую? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Удаляю старую БД..."
    ssh "$SERVER" "rm -f /data/finance-bot/db/finance_bot.db"
    print_success "БД удалена"
else
    print_info "БД не удаляется"
fi

# ─── Пересборка и запуск контейнера ───────────────────────────────────────────

print_header "Пересборка и запуск контейнера"

print_info "Пересобираю образ..."
ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml build --no-cache" > /dev/null 2>&1
print_success "Образ пересобран"

print_info "Запускаю контейнер..."
ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml up -d" > /dev/null 2>&1
print_success "Контейнер запущен"

# ─── Проверка статуса ─────────────────────────────────────────────────────────

print_header "Проверка статуса"

print_info "Жду 5 секунд для инициализации..."
sleep 5

print_info "Проверяю статус контейнера..."
STATUS=$(ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml ps --services --filter 'status=running'" 2>/dev/null || echo "")

if [[ "$STATUS" == *"finance-bot"* ]]; then
    print_success "Контейнер запущен и работает"
else
    print_warning "Контейнер может быть не готов, проверьте логи"
fi

# ─── Просмотр логов ───────────────────────────────────────────────────────────

print_header "Логи контейнера (последние 20 строк)"

ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml logs --tail=20"

# ─── Итоговое сообщение ───────────────────────────────────────────────────────

print_header "Обновление завершено"

print_success "Все файлы обновлены на сервере $SERVER"
print_info "Резервная копия сохранена: $BACKUP_DIR/$BACKUP_NAME"
print_info "Для просмотра логов используйте:"
echo "  ssh $SERVER \"cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml logs -f\""

echo ""
print_info "Для отката на предыдущую версию используйте:"
echo "  ssh $SERVER \"rm -rf $REMOTE_PATH && cp -r $BACKUP_DIR/$BACKUP_NAME $REMOTE_PATH && cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml up -d\""

echo ""
