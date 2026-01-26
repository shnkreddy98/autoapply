FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    libreoffice \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project definition
COPY pyproject.toml uv.lock ./

# Install dependencies (including playwright)
RUN uv sync --frozen --no-install-project

# Install Playwright browsers and dependencies
# This installs chromium and necessary system libraries
RUN uv run playwright install --with-deps chromium

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
