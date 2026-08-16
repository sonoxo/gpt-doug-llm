FROM python:3.11-slim

LABEL org.opencontainers.image.title="GPT Doug LLM"
LABEL org.opencontainers.image.description="Unified local-first agentic AI system"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/sonoxo/gpt-doug-llm"

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir pytest cryptography

# Copy project
COPY . .

# Create runtime directories
RUN mkdir -p /root/.gpt-doug /app/workers/tasks /app/workers/claimed \
    /app/workers/processed /app/workers/results /app/workers/live

# Default to the provider-neutral web interface.
ENV GPT_DOUG_PROVIDER=none
CMD ["python3", "web/server.py"]
