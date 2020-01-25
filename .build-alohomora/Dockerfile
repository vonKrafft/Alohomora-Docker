FROM python:3-alpine

WORKDIR /usr/src/app

COPY ./app /usr/src/app
RUN apk update \
    && apk add --no-cache gcc libressl-dev musl-dev libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del gcc

EXPOSE 8080

CMD [ "python", "./alohomora.py" ]
