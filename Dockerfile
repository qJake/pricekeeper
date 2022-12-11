FROM python:3.9-alpine

WORKDIR /app

RUN apk update
RUN apk add git
RUN git clone https://github.com/qJake/pricekeeper.git


FROM python:3.9-alpine

ENV DOCKER_APP=True
WORKDIR /app
EXPOSE 9600

RUN apk add curl make automake gcc

COPY --from=0 /app/pricekeeper /app

RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "main.py"]
