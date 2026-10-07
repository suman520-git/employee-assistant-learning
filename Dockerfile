FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["sh", "-c", "python initialize_app.py && exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"]