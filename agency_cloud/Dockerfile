FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN groupadd --system zyra && useradd --system --gid zyra --create-home zyra

COPY agency_cloud/requirements.txt /tmp/agency-requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/agency-requirements.txt

COPY . /app
RUN mkdir -p /app/agency_cloud/.data && chown -R zyra:zyra /app

USER zyra

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn agency_cloud.app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
