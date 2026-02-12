#!/bin/bash

# Start Xvfb (virtual display)
echo "Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 2

# Start x11vnc (VNC server to stream the display)
echo "Starting x11vnc on port 5900..."
x11vnc -display :99 -forever -nopw -listen 0.0.0.0 -shared -rfbport 5900 &
sleep 2
echo "x11vnc started"

# Set display environment variable
export DISPLAY=:99

# Start FastAPI application
echo "Starting FastAPI application..."
uv run fastapi run main.py --host 0.0.0.0 --port 8000

# Cleanup on exit
kill $XVFB_PID
