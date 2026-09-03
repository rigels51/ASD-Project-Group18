FROM python:3.11-slim
WORKDIR /app
COPY student-5/database/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY student-5/database/app.py .
COPY student-5/database/init_db.py .
RUN python init_db.py
EXPOSE 5022
CMD ["python", "app.py"]