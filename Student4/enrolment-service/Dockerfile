FROM python:3.11-slim

WORKDIR /app

COPY Student4/enrolment-service/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY Student4/enrolment-service ./enrolment-service

COPY prompts/service ./prompts/service
COPY prompts/lab4 ./prompts/lab4

EXPOSE 5001

CMD ["python", "enrolment-service/app.py"]