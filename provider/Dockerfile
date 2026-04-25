FROM python:3.12-slim

WORKDIR /app
COPY metatube_provider ./metatube_provider

ENV METATUBE_HOST=0.0.0.0
ENV METATUBE_PORT=8080

EXPOSE 8080
CMD ["python", "-m", "metatube_provider"]
