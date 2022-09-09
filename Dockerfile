FROM python:3.10.6-alpine

RUN apk add --no-cache --virtual gcc \
  && pip install --no-cache-dir --upgrade pip \
  && rm -rf /var/cache/apk/*

ADD pyproject.toml README.md  /requirements/
ADD neatpush/__init__.py /requirements/neatpush/

RUN pip install /requirements --no-cache-dir

ENV APP_DIR /neatpush
WORKDIR $APP_DIR
ADD . $APP_DIR

RUN pip install --editable .

CMD ["python", "-c", "import neatpush; print(neatpush.__version__)"]
