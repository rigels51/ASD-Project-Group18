FROM python:3.11-slim

WORKDIR /app

COPY ai-services/rag-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-services/rag-server/ ./

EXPOSE 5003

CMD ["python", "rag_http_server.py"]