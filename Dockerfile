FROM python:3.11-slim

LABEL org.opencontainers.image.title="GPT Doug LLM"
LABEL org.opencontainers.image.description="Unified local-first agentic AI system"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/sonoxo/gpt-doug-llm"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
RUN pip install --no-cache-dir pytest cryptography

# Copy project
COPY . .

# Create runtime directories
RUN mkdir -p /root/.gpt-doug /app/workers/tasks /app/workers/claimed \
    /app/workers/processed /app/workers/results /app/workers/live

# Default to the terminal client
ENTRYPOINT ["python3", "gpt-doug"]
