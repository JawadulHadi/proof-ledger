FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Collect with the production storage so the hashed manifest exists at runtime.
RUN DEBUG=0 SECRET_KEY=build-only-not-used python manage.py collectstatic --noinput
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
CMD ["sh", "start.sh"]
