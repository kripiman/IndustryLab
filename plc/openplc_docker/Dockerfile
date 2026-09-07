# ==============================================================================
# IndustryLab — OpenPLC IEC 61131-3 Dedicated Container Image
# ==============================================================================
FROM python:3.11-slim

LABEL maintainer="IndustryLab OT/ICS Cyber Range Team"
LABEL description="OpenPLC IEC 61131-3 Runtime with Modbus/TCP Support"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    net-tools \
    iproute2 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openplc

# Install Python requirements
RUN pip install --no-cache-dir \
    pymodbus==2.5.3 \
    pyyaml \
    requests

COPY . /opt/openplc/

EXPOSE 502 8080

CMD ["python3", "plc/openplc_runtime.py", "--process", "cooling", "--port", "502"]
