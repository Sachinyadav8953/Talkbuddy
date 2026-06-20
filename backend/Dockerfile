FROM python:3.10-slim

# Install system dependencies (specifically ffmpeg for audio transcription)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory inside user home
WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Expose API port (Hugging Face runs on 7860 by default, run.py reads PORT env var)
EXPOSE 7860

# Start server
CMD ["python", "run.py"]
