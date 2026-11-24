# syntax=docker/dockerfile:1
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
# .dockerignore で必要なファイルだけを許可しています (設定ファイル・DB・画像は含めません)。
COPY pyproject.toml README.md ./
COPY coc_skype_bot ./coc_skype_bot
RUN pip install . && rm -rf build ./*.egg-info

RUN useradd --create-home --uid 10001 bot
USER 10001
WORKDIR /home/bot

ENTRYPOINT ["coc-skype-bot"]
CMD ["demo"]
