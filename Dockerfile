# Orqestra: one container serving the FastAPI backend and the built React app from the same origin.

# ---- 1. Build the React frontend ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive --network-timeout 600000
COPY frontend/ ./
# Empty backend URL = call the API on the same origin (/api).
ENV REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false CI=false
RUN yarn build

# ---- 2. Python runtime ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt
COPY backend/ ./
COPY --from=web /web/build /app/frontend/build
ENV FRONTEND_BUILD_DIR=/app/frontend/build PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
