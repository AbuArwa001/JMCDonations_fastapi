FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution and installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv pip install --system -r pyproject.toml

COPY . .

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]
