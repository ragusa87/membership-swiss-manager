FROM python:3.13-bullseye AS base

RUN set -x; \
    apt-get update -qq \
    && apt-get install -yq \
        bash-completion \
        gettext \
        postgresql-client \
        sassc \
    && rm -rf /var/lib/apt/lists/*

ARG USER_ID=1000
ARG GROUP_ID=1000

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV VIRTUAL_ENV="/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN set -x; \
    groupadd -g $GROUP_ID app && \
    useradd --create-home -u $USER_ID -g app -s /bin/bash app && \
    install -o app -g app -d /app "$VIRTUAL_ENV"
RUN python -m ensurepip --upgrade
RUN python -m venv "$VIRTUAL_ENV"
RUN python -m pip install --upgrade pip
RUN python -m venv $VIRTUAL_ENV && chown -R ${USER_ID}:${GROUP_ID} $VIRTUAL_ENV
USER app

WORKDIR /app
COPY entrypoint.sh /
ENTRYPOINT [ "/entrypoint.sh" ]

FROM base AS build
USER app
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY --link . /app/

FROM base AS dev
USER app
COPY requirements.dev.txt /app/
RUN pip install -r requirements.dev.txt
COPY --link . /app/

