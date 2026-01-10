# Brain MCP Server

MCP server exposing Brain service operations as tools via FastMCP.

## Tools

- `save_to_brain` - Save thought with full metadata
- `quick_capture` - Quick capture with auto-classification
- `search_brain` - Search thoughts by text query
- `list_recent` - List recent entries with filters
- `get_entry` - Fetch specific entry by ID

## Transports

- **stdio** - Local development (default)
- **SSE** - Remote access via HTTP

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with stdio transport
python brain_mcp_server.py

# Run with SSE transport
MCP_PORT=8084 MCP_TRANSPORT=sse python brain_mcp_server.py

# Test with MCP inspector
mcp dev brain_mcp_server.py
```

## Docker Deployment

```bash
docker compose up -d
```

Builds from GitHub and runs with SSE transport on port 8084.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| BRAIN_API_BASE | http://192.168.15.6:8083 | Brain REST API URL |
| BRAIN_API_TIMEOUT | 30.0 | API timeout in seconds |
| MCP_TRANSPORT | stdio | Transport mode (stdio/sse) |
| MCP_PORT | 8084 | SSE server port |
| MCP_HOST | 0.0.0.0 | SSE server host |
