# syntax=docker/dockerfile:1

FROM ghcr.io/music-assistant/server:2.9.9@sha256:50666a6f8d7f87d53d993dc41860ab06dda11047f6e433bb5bdbcb6e309ac74c

ARG BUILD_VERSION=2.9.9-yoto.10
ARG BUILD_ARCH

COPY yoto/ /tmp/yoto/

RUN set -eux; \
    /app/venv/bin/uv pip install \
      --python /app/venv/bin/python \
      --no-cache \
      "yoto-api==4.3.2"; \
    providers_dir="$(/app/venv/bin/python -c \
      'import pathlib, music_assistant; print(pathlib.Path(music_assistant.__file__).parent / "providers")')"; \
    cp -a /tmp/yoto "${providers_dir}/yoto"; \
    rm -rf /tmp/yoto "${providers_dir}/yoto/__pycache__"; \
    /app/venv/bin/python -c \
      'import importlib.metadata, json, pathlib, music_assistant.providers.yoto, music_assistant.providers.yoto.provider; p = pathlib.Path(music_assistant.providers.yoto.__file__).parent; assert importlib.metadata.version("yoto-api") == "4.3.2"; assert json.loads((p / "manifest.json").read_text())["domain"] == "yoto"; assert all((p / name).is_file() for name in ("client.py", "catalogue.py", "provider.py", "pkce.py")); print("Yoto provider image check passed")'

LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}" \
      org.opencontainers.image.title="Music Assistant 2.9.9 with Yoto provider" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.base.digest="sha256:50666a6f8d7f87d53d993dc41860ab06dda11047f6e433bb5bdbcb6e309ac74c" \
      org.opencontainers.image.source="https://github.com/m4rkireland/music-assistant-yoto"
