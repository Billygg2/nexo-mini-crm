FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/data/db.sqlite3

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system crm && useradd --system --gid crm crm \
    && mkdir /data && chown crm:crm /data
COPY --chown=crm:crm . .
RUN python manage.py collectstatic --noinput
USER crm
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=3)"
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --access-logfile - --error-logfile -"]
