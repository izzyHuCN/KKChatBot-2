FROM python:3.9

WORKDIR /app

# Install system dependencies
# Even with full image, we install these to be safe for opencv-headless and mediapipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Fix for MediaPipe on slim images (sometimes needs protobuf manually or specific versions)
# But mainly, we ensure numpy is compatible.


# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
