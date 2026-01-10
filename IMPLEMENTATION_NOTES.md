# OAuth 2.0 Implementation Notes

## What Was Done

Added OAuth 2.0 support to the Brain MCP Server to satisfy Claude Code's requirements for remote SSE MCP servers.

## Files Modified

### brain_mcp_server.py

Added the following OAuth endpoints using FastMCP's `@mcp.custom_route()` decorator:

1. **`/.well-known/oauth-protected-resource`** (RFC 9728)
   - Returns OAuth Protected Resource Metadata
   - Tells clients where to find authorization servers
   - Lists supported scopes and bearer token methods

2. **`/.well-known/oauth-authorization-server`** (RFC 8414)
   - Returns OAuth Authorization Server Metadata
   - Provides authorization, token, and registration endpoint URLs
   - Advertises support for PKCE, DCR, and authorization code flow

3. **`/.well-known/openid-configuration`**
   - OpenID Connect discovery endpoint
   - Returns same metadata as oauth-authorization-server
   - Some clients may attempt OIDC discovery first

4. **`/register`** (RFC 7591)
   - Dynamic Client Registration endpoint
   - Accepts client metadata and issues client IDs
   - Simplified implementation (auto-approves all registrations)

5. **`/authorize`** (RFC 6749)
   - Authorization endpoint for OAuth code flow
   - Simplified implementation (auto-approves all requests)
   - Returns authorization code without user interaction

6. **`/token`** (RFC 6749)
   - Token exchange endpoint
   - Issues Bearer tokens for authorization codes
   - Simplified implementation (no validation)

### Configuration

Added environment variables:
- `OAUTH_ENABLED` - Advisory flag (default: false)
- `BASE_URL` - Base URL for OAuth metadata (default: http://{MCP_HOST}:{MCP_PORT})

## Files Created

1. **OAUTH_SETUP.md**
   - Comprehensive OAuth setup documentation
   - Configuration examples
   - Testing instructions
   - Claude Code integration guide
   - Security considerations and upgrade path

2. **test_oauth.sh**
   - Shell script to test all OAuth endpoints
   - Uses curl and jq for testing
   - Can be run against local or remote servers

3. **IMPLEMENTATION_NOTES.md**
   - This file
   - Technical implementation details

## Implementation Approach

### Why This Approach?

After researching FastMCP's OAuth capabilities, I chose a **minimal custom implementation** rather than using FastMCP's built-in OAuth providers because:

1. **Simplicity**: The requirements are "just need Claude Code to accept the server, not full multi-user auth"
2. **Minimal Dependencies**: Custom routes use only Starlette (already a FastMCP dependency)
3. **Full Control**: Can implement exactly what's needed without extra complexity
4. **No External Dependencies**: Doesn't require external OAuth providers or complex setup

### What Makes This "Simple"?

The implementation is intentionally simplified:

- **No token validation**: Server doesn't verify Bearer tokens on incoming requests
- **No PKCE validation**: Advertises PKCE support but doesn't validate challenges
- **Auto-approval**: Authorization requests are auto-approved without user consent
- **Simple tokens**: Issues random strings instead of signed JWTs
- **No state storage**: Doesn't store authorization codes, tokens, or client registrations
- **No client authentication**: Accepts all client registrations without verification

This satisfies Claude Code's discovery requirements while keeping the implementation under 200 lines.

### Standards Compliance

Despite the simplifications, the implementation:

- **Follows RFC schemas**: Returns correctly formatted metadata per specifications
- **Implements required endpoints**: All endpoints Claude Code needs for discovery
- **Uses correct HTTP methods**: GET for discovery, POST for registration/token
- **Returns proper status codes**: 201 for registration, 400 for errors
- **Includes all required fields**: Issuer, endpoints, supported methods, etc.

## Testing

### Manual Testing

```bash
# Start server in SSE mode
MCP_TRANSPORT=sse python3 brain_mcp_server.py

# Run test script
./test_oauth.sh http://localhost:8084
```

### Expected Behavior with Claude Code

When Claude Code connects to the server:

1. Claude Code requests `/.well-known/oauth-protected-resource`
2. Server returns metadata with authorization server location
3. Claude Code requests `/.well-known/oauth-authorization-server`
4. Server returns authorization server configuration
5. Claude Code may attempt Dynamic Client Registration at `/register`
6. Server issues client ID and accepts registration
7. Claude Code initiates authorization flow if needed
8. Server auto-approves and returns authorization code
9. Claude Code exchanges code for token at `/token`
10. Server issues Bearer token
11. Claude Code connects to SSE endpoint with token
12. Server accepts connection (doesn't validate token)

## Production Considerations

This implementation is suitable for:
- Development and testing
- Single-user deployments
- Internal/private networks
- Scenarios where OAuth discovery is needed but full security is not

For production use, see the "Upgrading to Production OAuth" section in OAUTH_SETUP.md.

## Research Sources

Implementation based on:

- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [FastMCP Documentation](https://gofastmcp.com/servers/auth/authentication)
- [How to Add OAuth2 Authentication to Your MCP SSE Server](https://newsletter.adaptiveengineer.com/p/how-to-add-oauth2-authentication)
- [Building Secure MCP Servers in 2025: OAuth Authentication](https://martinschroder.substack.com/p/building-secure-mcp-severs-in-2025)
- [WorkOS MCP Authorization Guide](https://workos.com/blog/mcp-authorization-in-5-easy-oauth-specs)
- [Scalekit OAuth for MCP Servers](https://www.scalekit.com/blog/implement-oauth-for-mcp-servers)

## Known Limitations

1. **No token validation**: Server doesn't check Bearer tokens on MCP requests
2. **No PKCE validation**: Code challenges are not verified
3. **No user consent**: All authorization requests are auto-approved
4. **No persistence**: Authorization codes and tokens are not stored
5. **No revocation**: No way to revoke issued tokens
6. **No refresh tokens**: Tokens expire but cannot be refreshed
7. **Simple token format**: Uses random strings instead of JWTs

## Next Steps

If deploying to production:

1. Add JWT token validation (see OAUTH_SETUP.md)
2. Implement PKCE challenge verification
3. Add user consent UI for authorization
4. Store authorization codes and tokens
5. Add client validation and management
6. Deploy behind HTTPS reverse proxy
7. Consider using external OAuth provider (Auth0, WorkOS, etc.)

## Dependencies

No additional dependencies required beyond existing requirements.txt:

- `mcp[cli]>=1.0.0` - FastMCP framework (includes Starlette)
- `httpx>=0.27.0` - HTTP client for Brain API calls

Starlette is used for request/response handling in custom routes and is already included with FastMCP.
