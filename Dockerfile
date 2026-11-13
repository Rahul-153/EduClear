# Stage 1: build the React app
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 1b: PayPal's official MCP server (agent orders); pinned and installed here so the runtime image needs no npm
FROM node:22-slim AS mcp
RUN npm install --prefix /opt/mcp @paypal/mcp@1.8.1

# Stage 2: FastAPI serves the API and the built app (one Render web service)
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=mcp /usr/local/bin/node /usr/local/bin/node
COPY --from=mcp /opt/mcp /opt/mcp
COPY backend backend
COPY scripts/college_model.py scripts/college_model.py
COPY scripts/partial_model.py scripts/partial_model.py
COPY data/colleges data/colleges
COPY data/admissions data/admissions
COPY data/cutoffs_2025.sqlite data/cutoffs_2025.sqlite
COPY data/round_history.sqlite data/round_history.sqlite
COPY data/supplied/branch_placements.csv data/supplied/branch_placements.csv
COPY --from=web /web/dist frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*'"]
