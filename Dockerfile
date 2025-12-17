FROM python:3.13-trixie AS base

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

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"
ENV VIRTUAL_ENV="/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV REQUIREMENT_FILE=requirements.txt

RUN set -x; \
    groupadd -g $GROUP_ID app && \
    useradd --create-home -u $USER_ID -g app -s /bin/bash app && \
    install -o app -g app -d /app "$VIRTUAL_ENV" \
RUN mkdir -p /app/.ruff_cache && chown -R app:app /app/.ruff_cache
RUN python -m ensurepip --upgrade
RUN python -m venv "$VIRTUAL_ENV"
RUN python -m pip install --upgrade pip
RUN python -m venv $VIRTUAL_ENV && chown -R ${USER_ID}:${GROUP_ID} $VIRTUAL_ENV


# Install locales package
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/*
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "fr_CH.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen
USER app
WORKDIR /app
COPY entrypoint.sh /
ENTRYPOINT [ "/entrypoint.sh" ]

FROM base AS prod
USER app
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY --link --chown=$USER_ID:$GROUP_ID . /app/
RUN ./manage.py compilemessages
RUN ./manage.py collectstatic --noinput

FROM prod AS dev
USER app
COPY requirements.dev.txt /app/
ENV REQUIREMENT_FILE=requirements.dev.txt
RUN pip install -r requirements.dev.txt
