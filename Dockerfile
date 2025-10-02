# Многоступенчатая сборка для оптимизации
# Этап сборки зависимостей
FROM python:3.10-slim-bullseye AS builder

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем poetry
RUN pip install --no-cache-dir poetry

# Копируем файлы проекта
WORKDIR /app
COPY pyproject.toml poetry.lock* ./

# Устанавливаем зависимости
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Финальный этап
FROM python:3.10-slim-bullseye

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные зависимости из builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Создаем пользователя для безопасности
RUN addgroup --system django \
    && adduser --system --ingroup django django

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем исходный код
COPY --chown=django:django . .

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE karakoldelivery.settings

# Устанавливаем права доступа
RUN chmod +x /app/entrypoint.sh

# Переключаемся на пользователя django
USER django

# Точка входа
ENTRYPOINT ["/app/entrypoint.sh"]
