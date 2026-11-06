# Imagem do ingestor (MQTT → PostgreSQL). Build a partir de applications/.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "paho-mqtt>=2.1" "psycopg[binary]>=3.2"
COPY coleta ./coleta
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "coleta.ingestor"]
