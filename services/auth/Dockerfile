# Dockerfile de l'Auth Service.
# Build depuis la RACINE du projet : docker build -f services/auth/Dockerfile .

FROM python:3.12-slim

WORKDIR /app/services/auth

COPY services/auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/auth/ .

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
