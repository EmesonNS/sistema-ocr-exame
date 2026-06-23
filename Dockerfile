FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /code appuser

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./alembic /code/alembic
COPY ./alembic.ini /code/alembic.ini
COPY ./entrypoint.sh /code/entrypoint.sh

RUN mkdir -p /code/uploads && chown -R appuser:appuser /code

USER appuser

ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test

USER root
COPY ./requirements-test.txt /code/requirements-test.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements-test.txt
USER appuser

ENTRYPOINT []
CMD ["pytest", "-q"]
