ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.21
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-pip jq && python3 -m venv /venv
COPY requirements.txt /tmp/requirements.txt
RUN /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY store.py ai.py server.py dashboard.py policy.py shopping_filter.py management.py encryption.py maintenance.py maintenance_ui.py /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
