#!/bin/bash
set -e

# Проверяем и создаем необходимые директории
echo "Проверка и создание директорий..."
mkdir -p /app/backups
mkdir -p /app/credentials  
mkdir -p /app/data
mkdir -p /app/sqlite/data
mkdir -p /app/static
mkdir -p /app/templates

# Проверяем права доступа к директории sqlite
echo "Проверка прав доступа к sqlite директории..."
if [ ! -w "/app/sqlite/data" ]; then
    echo "ОШИБКА: Нет прав записи в директорию /app/sqlite/data"
    ls -la /app/sqlite/
    exit 1
fi

echo "Все директории готовы. Запуск приложения..."
exec "$@" 