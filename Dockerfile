FROM python:3.12-slim

WORKDIR /app

# Ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Делаем entrypoint исполняемым
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "roomtime.wsgi:application", "--bind", "0.0.0.0:8000"]
