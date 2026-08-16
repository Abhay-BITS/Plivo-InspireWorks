FROM node:20-slim AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /srv

COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir .

COPY --from=web-build /web/dist ./web/dist

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
