# Imagem da API da tela (somente leitura). Build a partir de applications/.
FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY coleta ./coleta
COPY api ./api
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
