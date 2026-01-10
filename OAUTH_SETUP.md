# OAuth 2.0 Implementation for Brain MCP Server

## Current Status: NOT IN USE

**As of 2026-01-10, this OAuth implementation is not active.**

### What Happened

This OAuth implementation was written for the SSE transport, which requires OAuth discovery endpoints for remote MCP clients. During testing, we encountered a known MCP SDK race condition (#423) where requests arrived before SSE initialization completed.

We switched to streamable-http transport, which:

- Does not require OAuth discovery endpoints
- Uses a single `/mcp` endpoint instead of SSE's dual-endpoint architecture
- Avoids the session management complexity that caused the race condition

### Why This Code Remains

The OAuth endpoints (~150 lines in `brain_mcp_server.py`) are kept for reference because:

1. **Future internet access may use it** - When exposing Brain MCP to the internet, we may layer OAuth on top of Cloudflare Access for fine-grained tool permissions
2. **Standards reference** - The implementation correctly follows RFC 9728, 8414, 7591, and 6749
3. **Learning artifact** - Documents how MCP OAuth discovery works

### What We'll Actually Use for Internet Access

Per research in `mission-control/docs/designs/mcp-auth-library-research.md`:

```
Internet --> Cloudflare Tunnel --> Cloudflare Access (SSO) --> Brain MCP Server
```

- Cloudflare Access handles identity (SSO with Google, GitHub, etc.)
- FastMCP validates the `CF-Access-JWT-Assertion` header
- Optional: Add OAuth layer inside for tool-level permissions

### Current Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Transport | streamable-http | Via `MCP_TRANSPORT=http` |
| Endpoint | `/mcp` | Single endpoint, not SSE's `/sse` + `/messages` |
| Auth | None | LAN-only, firewall-restricted |
| OAuth endpoints | Present but unused | Code exists, not invoked |

---

## Historical Documentation (SSE Transport)

The following documentation describes the OAuth implementation for SSE transport. It is preserved for reference but does not reflect current operation.

---

## Overview (SSE Transport - Not Current)

The Brain MCP Server includes OAuth 2.0 support following the Model Context Protocol (MCP) authorization specification. This enables Claude Code and other MCP clients to discover and authenticate with the server when running in SSE (remote) mode.

## Implementation Details

### Standards Compliance

The implementation follows these RFCs:

- **RFC 9728**: OAuth 2.0 Protected Resource Metadata
- **RFC 8414**: OAuth 2.0 Authorization Server Metadata
- **RFC 7591**: OAuth 2.0 Dynamic Client Registration
- **RFC 6749**: OAuth 2.0 Authorization Framework

### Endpoints Implemented

| Endpoint | Purpose | Standard |
|----------|---------|----------|
| `/.well-known/oauth-protected-resource` | Resource metadata discovery | RFC 9728 |
| `/.well-known/oauth-authorization-server` | Authorization server metadata | RFC 8414 |
| `/.well-known/openid-configuration` | OpenID Connect discovery | OIDC |
| `/register` | Dynamic client registration | RFC 7591 |
| `/authorize` | Authorization code flow | RFC 6749 |
| `/token` | Token exchange | RFC 6749 |

## Simplified Implementation

This is a **simplified implementation** designed to satisfy Claude Code's OAuth discovery requirements with minimal complexity. It is suitable for:

- Development environments
- Single-user deployments
- Internal/private networks
- Scenarios where full OAuth security is not required

### When to Upgrade

The simple/auto-approval implementation is sufficient until any of these conditions apply:

| Trigger | Why Upgrade is Needed |
|---------|----------------------|
| Multi-user access | Need user consent UI, per-user tokens, session isolation |
| Public internet exposure | Need HTTPS, token validation, PKCE enforcement, rate limiting |
| Shared API access | Need client validation, token storage, revocation capability |
| Audit/compliance requirements | Need JWT with claims, request logging, token lifecycle tracking |
| Untrusted network | Need token signature verification, short expiration, refresh tokens |

**Current deployment:** Single-user, private network (192.168.x.x), auto-approval is appropriate.

### Security Considerations

The current implementation:

- **Auto-approves** authorization requests (no user consent UI)
- **Does not validate** PKCE challenges (though it advertises support)
- **Issues simple tokens** (not signed JWTs)
- **Does not verify** token signatures on requests
- **Does not store** authorization codes or tokens

**For production use**, you should:

1. Add proper token validation (JWT signature verification)
2. Implement PKCE challenge validation
3. Add user consent UI for authorization
4. Store and validate authorization codes
5. Implement token expiration and refresh
6. Add proper client validation and storage
7. Use HTTPS for all endpoints

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_ENABLED` | `false` | Enable OAuth endpoints (currently always active) |
| `BASE_URL` | `http://{MCP_HOST}:{MCP_PORT}` | Base URL for OAuth metadata |
| `MCP_HOST` | `127.0.0.1` | Server bind address |
| `MCP_PORT` | `8084` | Server port |
| `MCP_TRANSPORT` | `stdio` | Transport mode (`stdio` or `sse`) |

### Example Configuration

For local testing:

```bash
export MCP_TRANSPORT=sse
export MCP_HOST=127.0.0.1
export MCP_PORT=8084
export BASE_URL=http://127.0.0.1:8084
export OAUTH_ENABLED=true

python3 brain_mcp_server.py
```

For remote access (production):

```bash
export MCP_TRANSPORT=sse
export MCP_HOST=0.0.0.0
export MCP_PORT=8084
export BASE_URL=https://brain-mcp.yourdomain.com
export OAUTH_ENABLED=true

python3 brain_mcp_server.py
```

## Testing OAuth Endpoints

### Test Discovery Endpoints

```bash
# Test protected resource metadata
curl http://localhost:8084/.well-known/oauth-protected-resource

# Expected response:
{
  "resource": "http://localhost:8084",
  "authorization_servers": [
    {
      "issuer": "http://localhost:8084"
    }
  ],
  "scopes_supported": [
    "mcp:tools:read",
    "mcp:tools:write"
  ],
  "bearer_methods_supported": ["header"]
}

# Test authorization server metadata
curl http://localhost:8084/.well-known/oauth-authorization-server

# Expected response:
{
  "issuer": "http://localhost:8084",
  "authorization_endpoint": "http://localhost:8084/authorize",
  "token_endpoint": "http://localhost:8084/token",
  "registration_endpoint": "http://localhost:8084/register",
  "code_challenge_methods_supported": ["S256"],
  ...
}
```

### Test Client Registration

```bash
curl -X POST http://localhost:8084/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "redirect_uris": ["http://localhost:3000/callback"]
  }'

# Expected response:
{
  "client_id": "brain-mcp-client-1234567890abcdef",
  "client_id_issued_at": 1736524800,
  "client_name": "Test Client",
  "redirect_uris": ["http://localhost:3000/callback"]
}
```

### Test Authorization Flow

```bash
# 1. Request authorization code
curl "http://localhost:8084/authorize?client_id=test&redirect_uri=http://localhost/callback&response_type=code&state=xyz"

# Returns authorization code (auto-approved)

# 2. Exchange code for token
curl -X POST http://localhost:8084/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=auth_abc123&redirect_uri=http://localhost/callback"

# Expected response:
{
  "access_token": "brain_token_...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "mcp:tools:read mcp:tools:write"
}
```

## Claude Code Integration

### Adding to Claude Code

1. Start the server in SSE mode:
   ```bash
   MCP_TRANSPORT=sse python3 brain_mcp_server.py
   ```

2. In Claude Code, add the server to your MCP configuration:
   ```json
   {
     "mcpServers": {
       "brain": {
         "url": "http://192.168.15.6:8084",
         "transport": "sse"
       }
     }
   }
   ```

3. Claude Code will:
   - Discover OAuth endpoints via `/.well-known/oauth-protected-resource`
   - Attempt Dynamic Client Registration at `/register`
   - Follow the authorization flow if needed

### Expected Behavior

Since this is a simplified implementation:

- Claude Code should successfully discover the OAuth endpoints
- The server will auto-approve any authorization requests
- Tokens are issued without validation
- No user interaction is required

## Troubleshooting

### 404 Errors on .well-known Endpoints

If you see 404 errors when accessing `/.well-known/*` endpoints:

1. Ensure the server is running in SSE mode:
   ```bash
   MCP_TRANSPORT=sse python3 brain_mcp_server.py
   ```

2. Verify the endpoints are registered:
   ```bash
   curl http://localhost:8084/.well-known/oauth-protected-resource
   ```

3. Check the server logs for any startup errors

### Claude Code Connection Issues

If Claude Code cannot connect:

1. Verify the server is accessible from Claude Code's network
2. Check firewall rules allow traffic on port 8084
3. Ensure BASE_URL matches the URL Claude Code uses
4. Try accessing the discovery endpoint manually from the same network

### Import Errors

If you see import errors for `starlette`:

```bash
pip3 install starlette
```

Starlette should be installed as a dependency of FastMCP, but install it explicitly if needed.

## Upgrading to Production OAuth

To implement proper OAuth security:

1. **Token Validation**: Add JWT signature verification
   - Use `PyJWT` or similar library
   - Verify token signature, issuer, audience, expiration

2. **PKCE Validation**: Store and validate code challenges
   - Store PKCE challenge on authorization request
   - Validate code verifier on token request

3. **User Consent**: Add authorization UI
   - Present user with client details and requested scopes
   - Require explicit user approval

4. **State Management**: Implement proper storage
   - Store authorization codes (short TTL)
   - Store issued tokens with metadata
   - Implement token revocation

5. **Client Management**: Validate and store clients
   - Validate client metadata on registration
   - Store client configurations
   - Implement client authentication

6. **HTTPS**: Deploy behind reverse proxy
   - Use nginx or similar with SSL/TLS
   - Redirect HTTP to HTTPS
   - Set secure cookie flags

## References

- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [RFC 9728 - OAuth Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728.html)
- [RFC 8414 - OAuth Authorization Server Metadata](https://www.rfc-editor.org/rfc/rfc8414.html)
- [RFC 7591 - OAuth Dynamic Client Registration](https://www.rfc-editor.org/rfc/rfc7591.html)
- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)
- [FastMCP Authentication Guide](https://gofastmcp.com/servers/auth/authentication)
