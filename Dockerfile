# ---- build stage: install dependencies ----
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage: copy only what's needed to run ----
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src ./src
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
