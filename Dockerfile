FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
COPY start.sh .
RUN chmod +x start.sh
# Expose port
EXPOSE 8000

# Start command
CMD ["./start.sh"]
