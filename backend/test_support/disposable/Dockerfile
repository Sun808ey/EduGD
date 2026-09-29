FROM python:3.12-slim
WORKDIR /backend
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY app ./app
COPY migrations ./migrations
COPY tests ./tests
COPY test_support ./test_support
COPY scripts ./scripts
COPY pytest.ini pyproject.toml run.py ./
CMD ["python", "-m", "test_support.disposable.run"]
