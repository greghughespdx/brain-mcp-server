FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY brain_mcp_server.py .

# Environment variables with defaults
ENV BRAIN_API_BASE=https://n8n.gregslab.org/webhook
ENV BRAIN_API_TIMEOUT=30.0
ENV MCP_TRANSPORT=sse
ENV MCP_PORT=8084
ENV MCP_HOST=0.0.0.0

# Expose port
EXPOSE 8084

# Run server with SSE transport
CMD ["python", "-u", "brain_mcp_server.py"]
