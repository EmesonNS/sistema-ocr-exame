FROM python:3.10-slim

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