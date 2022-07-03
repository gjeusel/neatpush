FROM python:3.10.5-bullseye

RUN apt-get update \
  && apt-get install --no-install-recommends -y git gcc \
  && pip install --no-cache-dir --upgrade pip \
  && rm -rf /var/lib/apt/lists/*

ADD pyproject.toml README.md  /requirements/
ADD neatpush/__init__.py /requirements/neatpush/

RUN pip install /requirements --no-cache-dir
RUN pip install git+https://github.com/edgedb/edgedb-python@14f8a32ca415fee1219d62343cfbca239eaa12d1

ENV APP_DIR /neatpush
WORKDIR $APP_DIR
ADD . $APP_DIR

RUN pip install --editable .

CMD ["python", "-c", "import neatpush; print(neatpush.__version__)"]
