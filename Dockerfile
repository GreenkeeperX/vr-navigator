FROM python:3.13-alpine

# Unprivilegierter Benutzer; /data gehört ihm, damit ein neues Volume beschreibbar ist
RUN addgroup -g 10001 app && adduser -D -H -u 10001 -G app app \
    && mkdir /data && chown app:app /data

WORKDIR /srv
COPY app ./app
ENV DATA_DIR=/data PORT=8788 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
VOLUME /data
EXPOSE 8788
USER 10001:10001
CMD ["python", "-m", "app.server"]
