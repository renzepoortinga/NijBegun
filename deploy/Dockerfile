# Nij Begun isolatieplan-webapp — productie-image (waitress achter Caddy)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV NIJBEGUN_PROD=1 NIJBEGUN_HTTPS=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "dashboard/app.py", "--serve"]
