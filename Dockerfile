FROM python:3.10-slim

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=pypi.org

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
