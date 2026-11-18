FROM python:3.12-slim

WORKDIR /app

COPY requirements-pg.txt /app/requirements-pg.txt
RUN pip install --no-cache-dir -r /app/requirements-pg.txt

COPY app /app/app

ENV PYTHONUNBUFFERED=1
EXPOSE 8010

CMD ["python", "app/server.py", "--port", "8010"]
