FROM python:3.12-alpine
RUN addgroup -S takos && adduser -S -G takos takos \
    && mkdir -p /app /data && chown -R takos:takos /app /data
WORKDIR /app
COPY --chown=takos:takos . /app/
USER takos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TAK_OS_CONTAINER=1
ENV TAK_OS_DB=/data/gateway.sqlite3
EXPOSE 8080
CMD ["python3", "-u", "gateway.py", "--bind", "0.0.0.0", "--port", "8080"]
