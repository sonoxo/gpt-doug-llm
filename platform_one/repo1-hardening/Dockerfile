ARG BASE_REGISTRY=registry1.dso.mil
ARG BASE_IMAGE=ironbank/redhat/ubi/ubi9-minimal
ARG BASE_TAG=9.8

FROM ${BASE_REGISTRY}/${BASE_IMAGE}:${BASE_TAG}

ARG APP_UID=1001
ARG CORE_FILE=core.py

RUN microdnf -y update && \
    microdnf -y install python3 && \
    microdnf clean all && \
    mkdir -p /opt/qbio && \
    chown -R ${APP_UID}:0 /opt/qbio && \
    chmod -R g=u /opt/qbio

WORKDIR /opt/qbio

COPY --chown=${APP_UID}:0 ${CORE_FILE} /opt/qbio/core.py
COPY --chown=${APP_UID}:0 scripts/service.py /opt/qbio/service.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

USER 1001

ENTRYPOINT ["python3", "/opt/qbio/service.py"]
