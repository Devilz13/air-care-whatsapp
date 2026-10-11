FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY aircare /app/aircare
RUN useradd --uid 10001 --create-home aircare && mkdir /app/data && chown aircare:aircare /app/data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AIRCARE_DB=/app/data/aircare.db
EXPOSE 8080
CMD ["python", "-m", "aircare.server"]
