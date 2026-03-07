# Use official Python lightweight image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better Docker layer caching
COPY ml_risk_engine/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML Engine source code + the pre-trained models and datasets
COPY ml_risk_engine/ ./ml_risk_engine/
COPY logs/ ./logs/

# Expose the FastAPI port
EXPOSE 8000

# Specify PYTHONPATH so the modules can find each other
ENV PYTHONPATH=/app/ml_risk_engine

# Start the ML Risk Engine FastAPI server
CMD ["uvicorn", "ml_risk_engine.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
