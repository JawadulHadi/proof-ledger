# syntax=docker/dockerfile:1

# Build the React + TypeScript client first. Vite writes to ../core/static/app, i.e.
# /core/static/app from this stage's working directory.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
COPY --from=frontend /core/static/app ./core/static/app
# Collect with the production storage so the hashed manifest exists at runtime.
RUN DEBUG=0 SECRET_KEY=build-only-not-used python manage.py collectstatic --noinput
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
CMD ["sh", "start.sh"]
