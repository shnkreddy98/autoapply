FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies for Playwright + Xvfb for virtual display + VNC for viewing + LibreOffice for PDF conversion
RUN apt-get update && apt-get install -y \
    curl \
    xvfb \
    x11vnc \
    libreoffice-core \
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

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose ports
EXPOSE 8000 5900

# Run the startup script (starts Xvfb, VNC, and FastAPI)
CMD ["/app/start.sh"]
