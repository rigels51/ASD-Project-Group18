FROM python:3.11-slim

WORKDIR /app

COPY student-5/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/backend ./student-5/backend
COPY student-5/prompts ./student-5/prompts

WORKDIR /app/student-5/backend

EXPOSE 5021

CMD ["python", "app.py"]