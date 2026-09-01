FROM python:3.13-slim

ARG HTMLNINEFOX_WHEEL=dist/htmlninefox-0.3.0b2-py3-none-any.whl
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV HOME=/home/fox

RUN useradd --create-home --uid 10001 fox
WORKDIR /app
COPY ${HTMLNINEFOX_WHEEL} /tmp/htmlninefox.whl
RUN python -m pip install --no-cache-dir /tmp/htmlninefox.whl && rm /tmp/htmlninefox.whl

USER fox
VOLUME ["/home/fox/.htmlninefox", "/home/fox/htmlninefox-output"]
EXPOSE 8620
CMD ["htmlninefox", "serve", "--host", "0.0.0.0", "--port", "8620", "--output", "/home/fox/htmlninefox-output"]
