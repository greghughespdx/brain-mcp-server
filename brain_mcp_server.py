#!/usr/bin/env python3
"""Brain MCP Server - Exposes Brain service operations as MCP tools.

This server wraps the Brain REST API (sqlite-rest.py) to provide MCP-compatible
tools for capturing, searching, and managing thoughts in the Brain service.
"""
import os
from typing import Any, Optional
from datetime import datetime
import uuid

import httpx
from mcp.server.fastmcp import FastMCP

# API configuration
API_BASE = os.getenv("BRAIN_API_BASE", "http://192.168.15.6:8083")
API_TIMEOUT = float(os.getenv("BRAIN_API_TIMEOUT", "30.0"))

# MCP transport configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8084"))
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")

# Initialize FastMCP server with host/port for SSE transport
mcp = FastMCP("brain-mcp-server", host=MCP_HOST, port=MCP_PORT)


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
    source: str = "mcp-client",
    status: str = "inbox"
) -> dict[str, Any]:
    """Create entry payload for Brain API."""
    now = datetime.utcnow().isoformat() + "Z"
    entry_id = str(uuid.uuid4())

    return {
        "id": entry_id,
        "created": now,
        "updated": now,
        "source": source,
        "raw_text": text,
        "title": title or "Untitled",
        "status": status,
        "type": type_,
        "domain": domain
    }


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

    result = await make_api_request("POST", "/brain/entries", json_data=payload)

    return f"Thought saved to Brain.\nID: {result['id']}\nStatus: {result['status']}\n\nAuto-classification in progress..."


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

    result = await make_api_request("POST", "/brain/entries", json_data=payload)

    return f"Thought captured.\nID: {result['id']}\n\nAuto-classification in progress..."


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
    results = await make_api_request("GET", "/brain/search", params=params)

    if not results:
        return "No results found."

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

    results = await make_api_request("GET", "/brain/entries", params=params)

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
    entry = await make_api_request("GET", f"/brain/entries/{entry_id}")

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


if __name__ == "__main__":
    # Support both stdio (local) and SSE (remote) transports
    # Detect transport mode based on MCP_PORT environment variable
    transport_mode = os.getenv("MCP_TRANSPORT", "stdio")

    if transport_mode == "sse":
        # Run with SSE transport for remote access
        print(f"Starting Brain MCP server with SSE transport on {MCP_HOST}:{MCP_PORT}")
        mcp.run(transport="sse")
    else:
        # Run with stdio transport for local development
        print("Starting Brain MCP server with stdio transport")
        mcp.run()
