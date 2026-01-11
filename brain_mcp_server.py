#!/usr/bin/env python3
"""Brain MCP Server - Exposes Brain service operations as MCP tools.

This server wraps the Brain REST API (sqlite-rest.py) to provide MCP-compatible
tools for capturing, searching, and managing thoughts in the Brain service.
"""
import os
from typing import Any, Optional
from datetime import datetime
import uuid
import json

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.requests import Request

# API configuration
API_BASE = os.getenv("BRAIN_API_BASE", "https://n8n.gregslab.org/webhook")
API_TIMEOUT = float(os.getenv("BRAIN_API_TIMEOUT", "30.0"))

# MCP transport configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8084"))
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")

# OAuth configuration
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
BASE_URL = os.getenv("BASE_URL", f"http://{MCP_HOST}:{MCP_PORT}")

# Initialize FastMCP server with host/port and stateless HTTP mode
# stateless_http=True: Each request is independent (no session management)
# This is required for Claude Code's HTTP MCP client which doesn't maintain sessions
mcp = FastMCP("brain-mcp-server", host=MCP_HOST, port=MCP_PORT, stateless_http=True)


# OAuth metadata endpoints
@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource(request: Request):
    """OAuth 2.0 Protected Resource Metadata (RFC 9728).

    Provides discovery information for OAuth clients about this MCP server.
    """
    metadata = {
        "resource": BASE_URL,
        "authorization_servers": [
            {
                "issuer": BASE_URL,
            }
        ],
        "scopes_supported": [
            "mcp:tools:read",
            "mcp:tools:write",
        ],
        "bearer_methods_supported": ["header"]
    }
    return JSONResponse(metadata)


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_authorization_server(request: Request):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414).

    Provides authorization server configuration for OAuth clients.
    """
    metadata = {
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/authorize",
        "token_endpoint": f"{BASE_URL}/token",
        "registration_endpoint": f"{BASE_URL}/register",
        "code_challenge_methods_supported": ["S256"],
        "grant_types_supported": ["authorization_code"],
        "response_types_supported": ["code"],
        "scopes_supported": [
            "mcp:tools:read",
            "mcp:tools:write",
        ],
        "token_endpoint_auth_methods_supported": ["none"],
        "client_id_metadata_document_supported": True,
    }
    return JSONResponse(metadata)


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration(request: Request):
    """OpenID Connect Discovery metadata.

    Some clients may attempt OpenID Connect discovery.
    """
    # Return the same metadata as oauth-authorization-server
    return await oauth_authorization_server(request)


@mcp.custom_route("/register", methods=["POST"])
async def register_client(request: Request):
    """Dynamic Client Registration (RFC 7591).

    Simplified implementation that accepts all registrations.
    In production, this should validate and store client metadata.
    """
    try:
        client_metadata = await request.json()

        # Generate a client ID based on the client_id_metadata_document URL if provided
        # or generate a random one
        if "client_id" in client_metadata and client_metadata["client_id"].startswith("http"):
            client_id = client_metadata["client_id"]
        else:
            client_id = f"brain-mcp-client-{uuid.uuid4().hex[:16]}"

        # Return registration response
        response = {
            "client_id": client_id,
            "client_id_issued_at": int(datetime.now().timestamp()),
            **client_metadata
        }

        return JSONResponse(response, status_code=201)
    except Exception as e:
        return JSONResponse(
            {"error": "invalid_client_metadata", "error_description": str(e)},
            status_code=400
        )


@mcp.custom_route("/authorize", methods=["GET", "POST"])
async def authorize(request: Request):
    """Authorization endpoint (RFC 6749).

    Simplified implementation for demonstration. In production, this should:
    - Validate the client
    - Present user consent UI
    - Generate and store authorization codes
    """
    params = dict(request.query_params)

    # For demonstration, auto-approve and return authorization code
    # In production, this would involve user interaction
    auth_code = f"auth_{uuid.uuid4().hex}"
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")

    # Construct redirect URL
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"

    # Return redirect (in real implementation, would redirect after user consent)
    return JSONResponse({
        "redirect_url": redirect_url,
        "code": auth_code,
        "message": "Auto-approved for demonstration purposes"
    })


@mcp.custom_route("/token", methods=["POST"])
async def token_endpoint(request: Request):
    """Token endpoint (RFC 6749).

    Simplified implementation that issues tokens without validation.
    In production, this should:
    - Validate authorization codes
    - Validate PKCE challenge
    - Issue properly signed JWT tokens
    """
    try:
        form_data = await request.form()
        grant_type = form_data.get("grant_type")

        if grant_type == "authorization_code":
            # Generate a simple token (in production, this would be a signed JWT)
            access_token = f"brain_token_{uuid.uuid4().hex}"

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp:tools:read mcp:tools:write",
            }

            return JSONResponse(response)
        else:
            return JSONResponse(
                {"error": "unsupported_grant_type"},
                status_code=400
            )
    except Exception as e:
        return JSONResponse(
            {"error": "invalid_request", "error_description": str(e)},
            status_code=400
        )


# Helper functions
async def make_api_request(
    method: str,
    path: str,
    json_data: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, str]] = None
) -> dict[str, Any]:
    """Make HTTP request to Brain API."""
    url = f"{API_BASE}{path}"

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, json=json_data)
            elif method == "PUT":
                response = await client.put(url, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"API error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"Network error: {str(e)}")


def create_entry_payload(
    text: str,
    title: Optional[str] = None,
    type_: Optional[str] = None,
    domain: Optional[str] = None,
    source: str = "mcp-client"
) -> dict[str, Any]:
    """Create entry payload for n8n brain-capture webhook.

    Note: type_ and domain are accepted but may be overwritten by Ollama classification.
    See Brain entry 59830269 for tech debt documentation.
    """
    payload = {
        "text": text,
        "source": source
    }
    # Optional fields - only include if provided
    if title:
        payload["title"] = title
    if type_:
        payload["type"] = type_
    if domain:
        payload["domain"] = domain
    return payload


# MCP Tool Handlers using FastMCP decorators
@mcp.tool()
async def save_to_brain(
    text: str,
    title: Optional[str] = None,
    type: Optional[str] = None,
    domain: Optional[str] = None,
    source: str = "mcp-client"
) -> str:
    """Save a thought to Brain with full metadata.

    Use this when you have specific type/domain information or want to provide
    a custom title. The thought will be auto-classified by the Brain service.

    Args:
        text: The thought content to capture
        title: Optional custom title (auto-generated if not provided)
        type: Optional thought type (idea, task, question, observation, reflection, reference, problem)
        domain: Optional domain (aviation, aircraft-build, dev, homelab, personal, business)
        source: Optional source identifier (defaults to 'mcp-client')

    Returns:
        Confirmation message with entry ID and status
    """
    payload = create_entry_payload(
        text=text,
        title=title,
        type_=type,
        domain=domain,
        source=source
    )

    result = await make_api_request("POST", "/brain-capture", json_data=payload)

    return f"Thought saved to Brain.\nID: {result['entry']['id']}\nStatus: {result['entry']['status']}\n\nAuto-classification in progress..."


@mcp.tool()
async def quick_capture(text: str) -> str:
    """Quickly capture a thought with minimal input.

    Just provide the text - Brain will auto-classify type, domain, and generate a title.

    Args:
        text: The thought to capture

    Returns:
        Confirmation message with entry ID
    """
    payload = create_entry_payload(text=text, source="mcp-client")

    result = await make_api_request("POST", "/brain-capture", json_data=payload)

    return f"Thought captured.\nID: {result['entry']['id']}\n\nAuto-classification in progress..."


@mcp.tool()
async def search_brain(query: str, limit: int = 20) -> str:
    """Search for thoughts in Brain by text query.

    Searches both raw_text and title fields. Returns up to 20 matching entries by default.

    Args:
        query: Search query text
        limit: Maximum results to return (default: 20)

    Returns:
        Formatted list of matching entries
    """
    params = {"q": query}
    results = await make_api_request("GET", "/brain-search", params=params)

    if not results:
        return "No results found."

    # Normalize to list (n8n may return single object or array)
    if isinstance(results, dict):
        results = [results]

    # Format results
    output_lines = [f"Found {len(results)} result(s):\n"]
    for entry in results[:limit]:
        output_lines.append(f"• {entry.get('title', 'Untitled')}")
        output_lines.append(f"  ID: {entry['id']}")
        output_lines.append(f"  Type: {entry.get('type', 'unknown')} | Domain: {entry.get('domain', 'uncategorized')}")
        output_lines.append(f"  Created: {entry.get('created', 'unknown')}")
        output_lines.append("")

    return "\n".join(output_lines)


@mcp.tool()
async def list_recent(
    limit: int = 50,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    type: Optional[str] = None
) -> str:
    """List recent Brain entries with optional filters.

    Returns entries ordered by creation date (newest first).

    Args:
        limit: Maximum entries to return (default: 50)
        status: Filter by status (inbox, triaged, developing, graduated, archived)
        domain: Filter by domain
        type: Filter by type

    Returns:
        Formatted list of recent entries
    """
    params = {}
    if limit:
        params["limit"] = str(limit)
    if status:
        params["status"] = status
    if domain:
        params["domain"] = domain
    if type:
        params["type"] = type

    results = await make_api_request("GET", "/brain-list", params=params)

    if not results:
        return "No entries found."

    # Format results
    output_lines = [f"Recent entries ({len(results)}):\n"]
    for entry in results:
        output_lines.append(f"• {entry.get('title', 'Untitled')}")
        output_lines.append(f"  ID: {entry['id']}")
        output_lines.append(f"  Type: {entry.get('type', 'unknown')} | Domain: {entry.get('domain', 'uncategorized')} | Status: {entry.get('status', 'unknown')}")
        output_lines.append(f"  Created: {entry.get('created', 'unknown')}")
        output_lines.append("")

    return "\n".join(output_lines)


@mcp.tool()
async def get_entry(entry_id: str) -> str:
    """Fetch a specific Brain entry by ID.

    Returns full entry details including raw_text, metadata, and classification results.

    Args:
        entry_id: UUID of the entry to fetch

    Returns:
        Formatted entry details
    """
    entry = await make_api_request("GET", "/brain-get", params={"id": entry_id})

    if not entry:
        return f"Entry {entry_id} not found."

    # Format entry details
    output_lines = [
        f"Title: {entry.get('title', 'Untitled')}",
        f"ID: {entry['id']}",
        f"Type: {entry.get('type', 'unknown')}",
        f"Domain: {entry.get('domain', 'uncategorized')}",
        f"Status: {entry.get('status', 'unknown')}",
        f"Source: {entry.get('source', 'unknown')}",
        f"Created: {entry.get('created', 'unknown')}",
        f"Updated: {entry.get('updated', 'unknown')}",
        f"Confidence: {entry.get('confidence', 0)}",
        "",
        "Content:",
        entry.get('raw_text', '(empty)')
    ]

    return "\n".join(output_lines)


# Workaround for Claude Code Accept header bug (issue #15523)
# Claude Code's HTTP MCP client doesn't send required Accept header
# We use ASGI middleware to inject the header before MCP SDK validates it
class AcceptHeaderMiddleware:
    """ASGI middleware that fixes missing Accept header for /mcp endpoint."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") == "/mcp":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()

            if not accept or accept == "*/*" or "text/event-stream" not in accept:
                # Rebuild headers with fixed Accept
                new_headers = [(k, v) for k, v in scope["headers"] if k.lower() != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope)
                scope["headers"] = new_headers
                print("[Accept Header Fix] Fixed Accept header for /mcp request")

        await self.app(scope, receive, send)


if __name__ == "__main__":
    # Support stdio (local), SSE (legacy), and streamable-http (recommended) transports
    transport_mode = os.getenv("MCP_TRANSPORT", "stdio")

    if transport_mode == "http" or transport_mode == "streamable-http":
        # Run with streamable HTTP transport (recommended for network access)
        # Avoids SSE initialization race condition (MCP SDK issue #423)
        print(f"Starting Brain MCP server with streamable-http transport on {MCP_HOST}:{MCP_PORT}")
        print(f"MCP endpoint: http://{MCP_HOST}:{MCP_PORT}/mcp")

        # Get the Starlette app from FastMCP
        app = mcp.streamable_http_app()

        # Wrap with Accept header fix middleware
        # (Workaround for Claude Code bug #15523 - HTTP MCP client missing Accept header)
        wrapped_app = AcceptHeaderMiddleware(app)
        print("[Accept Header Fix] Applied ASGI middleware wrapper")

        # Run with uvicorn directly
        import uvicorn
        uvicorn.run(wrapped_app, host=MCP_HOST, port=MCP_PORT)
    elif transport_mode == "sse":
        # Run with SSE transport (legacy, has known race conditions)
        print(f"Starting Brain MCP server with SSE transport on {MCP_HOST}:{MCP_PORT}")
        print("WARNING: SSE transport has known initialization race conditions")
        mcp.run(transport="sse")
    else:
        # Run with stdio transport for local development
        print("Starting Brain MCP server with stdio transport")
        mcp.run()
