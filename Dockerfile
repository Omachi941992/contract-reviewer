FROM python:3.12-slim

WORKDIR /app

# Cài dependencies trước (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port
EXPOSE 8080

# Dùng gunicorn cho production (không dùng Flask dev server)
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "180", "app:app"]
