# Используем официальный образ Python
FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы приложения
COPY . .

# Устанавливаем переменные окружения для PostgreSQL
ENV DATABASE_URL=postgresql://lalexl:1232@db:5432/mars

# Открываем порт (если необходимо)
EXPOSE 5000

# Команда для запуска бота
CMD ["python", "main.py"]
