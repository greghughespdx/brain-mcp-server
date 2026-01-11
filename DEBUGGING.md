# Brain MCP Server - Claude Code Accept Header Debug Log

## Issue Summary
Claude Code's HTTP MCP client doesn't send the required `Accept: application/json, text/event-stream` header, causing the MCP Python SDK's streamable-http transport to reject requests with "Not Acceptable" errors.

## Root Cause
- **Claude Code bug**: https://github.com/anthropics/claude-code/issues/15523
- **MCP SDK strict validation**: https://github.com/modelcontextprotocol/python-sdk/issues/1641

## Attempted Solutions

### 1. Starlette Middleware (Failed)
- Tried to add middleware via `mcp.app.add_middleware()`
- FastMCP doesn't expose `.app` attribute
- Would require access to FastMCP internals

### 2. ASGI Wrapper (Failed)
- Tried to wrap the ASGI app before passing to uvicorn
- Couldn't access transport.asgi_app without manually creating transport
- FastMCP.run() abstracts this away

### 3. Uvicorn Monkey-Patch (Current Attempt - Hanging)
- Patching `uvicorn.protocols.http.h11_impl.H11Protocol.handle_events`
- Async method being called synchronously
- Causes requests to hang

## Current Investigation
Need to patch at a point where:
1. We can intercept the ASGI scope before MCP transport sees it
2. The patch point is synchronous OR properly async
3. It works with FastMCP.run()

## Next Steps
- Try patching at ASGI middleware layer with proper async handling
- OR patch the h11 protocol's connection handling before handle_events
- OR use a reverse proxy (nginx/caddy) to fix headers externally
