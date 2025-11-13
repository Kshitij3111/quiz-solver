# Use official lightweight Python image
FROM python:3.11-slim

# Install system deps for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libatk1.0-data libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Make directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Expose port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
