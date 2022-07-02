FROM python:3.10.5-slim-buster

# RUN apt-get update \
#   && apt-get install --no-install-recommends -y gcc git \
#   && pip install --no-cache-dir --upgrade pip \
#   && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

ADD pyproject.toml README.md  /requirements/
ADD neatpush/__init__.py /requirements/neatpush/

RUN pip install /requirements --no-cache-dir

ENV APP_DIR /neatpush
WORKDIR $APP_DIR
ADD . $APP_DIR

RUN pip install --editable .

CMD ["python", "-c", "import neatpush; print(neatpush.__version__)"]
