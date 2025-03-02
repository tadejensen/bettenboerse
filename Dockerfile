FROM python:3.12-alpine3.21 AS builder
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry build --format=wheel


FROM python:3.12-alpine3.21
ENV PYTHONUNBUFFERED=TRUE

RUN adduser -D bettenboerse
COPY --from=builder /app/dist/bettenboerse*.whl .
# git is needed to install dep from git
RUN apk add --no-cache git && \
    pip install bettenboerse*.whl && \
    rm bettenboerse*.whl

USER bettenboerse
EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/bettenboerse"]
