FROM python:3.11-slim

WORKDIR /backend

# Evita que Python escriba archivos .pyc y fuerza a que el output de consola no se bloquee
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /backend/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]