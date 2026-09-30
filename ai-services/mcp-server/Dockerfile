FROM python:3.11-slim

WORKDIR /app

COPY ai-services/mcp-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-services/mcp-server/ ./

EXPOSE 8000

CMD ["python", "server.py"]