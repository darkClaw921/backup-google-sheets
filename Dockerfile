# Используем официальный образ Python 3.12 slim для оптимизации размера
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv для управления зависимостями
RUN pip install uv

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости
RUN uv sync --frozen

# Копируем весь код приложения
COPY . .

# Создаем необходимые директории с правами root
RUN mkdir -p backups credentials data sqlite/data static templates

# Меняем владельца файлов на пользователя app ПОСЛЕ создания директорий
RUN chown -R app:app /app

# Убеждаемся что директория sqlite имеет правильные права
RUN chmod -R 755 /app/sqlite

# Копируем entrypoint скрипт и делаем его исполняемым
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Переключаемся на пользователя app
USER app

# Открываем порт 8000
EXPOSE 8000

# Устанавливаем curl для healthcheck
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER app

# Добавляем healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Устанавливаем entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Команда запуска приложения
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 