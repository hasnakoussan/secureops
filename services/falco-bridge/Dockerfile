# Dockerfile du Falco Bridge Service.
# Build depuis la RACINE du projet : docker build -f services/falco-bridge/Dockerfile .

FROM python:3.12-slim

WORKDIR /app/services/falco-bridge

COPY services/falco-bridge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/falco-bridge/ .

EXPOSE 8006

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8006"]
