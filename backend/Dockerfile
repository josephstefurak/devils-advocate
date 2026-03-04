FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake knowledge base into image
COPY knowledge_base/ ./knowledge_base/

EXPOSE 8080

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "8080"]
