FROM python:3.11-alpine

WORKDIR /app

# Copy the conservation monitor and core module
COPY conservation_monitor.py .
COPY core/ core/

# Ensure Python output is unbuffered (docker-friendly logging)
ENV PYTHONUNBUFFERED=1

# Default PLATO URL (overridden by fleet-stack networking)
ENV PLATO_URL=http://plato:8847
ENV POLL_INTERVAL=60
ENV MONITORED_ROOMS=research_log,fleet_math,event-bus

CMD ["python3", "conservation_monitor.py"]
