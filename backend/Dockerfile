# Use a lightweight Python base image
FROM python:3.9-slim

# Set a working directory inside the container
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code into /app
COPY . .

# Expose port 8080 for local testing (not strictly required by Cloud Run)
EXPOSE 8080

# Set the entry point to run your socket_server
CMD ["python", "socket_server.py"]