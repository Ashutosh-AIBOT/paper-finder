FROM python:3.11-slim
WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# EXPOSE $PORT is not required by Docker itself but is good for documentation
# CMD will use the $PORT environment variable assigned by Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
