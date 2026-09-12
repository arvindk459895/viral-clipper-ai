FROM python:3.10-slim

# Install system dependencies: FFmpeg, libsndfile, git, curl, OpenCV runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY . .

# Cloud Run default port is 8080 (or $PORT environment variable)
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Launch Streamlit web app using PORT dynamically
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
