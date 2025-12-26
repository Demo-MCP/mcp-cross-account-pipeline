AWS Kiro — Implement tool-tier segregation in Broker using /ask (user) and /admin (admin)

SCOPE
- Add a second broker route: POST /admin
- /admin exposes ALL tools (superset)
- /ask exposes APPROVED SUBSET only
- Do NOT implement auth/mtls checks in this change (Suhaib will handle next iteration)
- Still enforce “fail-closed” tool gating so models cannot call tools not allowed for the endpoint

CURRENT
- Broker ALB stays the same (existing)
- MCP Gateway ALB stays the same (existing)
- Broker already aggregates tools from MCP endpoints (iac, ecs, pricingcalc, metrics, pr)

GOAL BEHAVIOR
- POST /ask:
  - Broker only advertises USER_ALLOWED tools to the model
  - Broker only executes USER_ALLOWED tool calls
- POST /admin:
  - Broker advertises ALL tools to the model
  - Broker executes ALL tool calls

-----------------------------------------
STAGE 1 — Add endpoint routing and request “tier”
-----------------------------------------
1) In broker FastAPI app:
   - Keep existing POST /ask handler
   - Add new POST /admin handler
2) Both handlers call a shared internal function:
   handle_request(request, tier="user"|"admin")

Example:
- /ask   -> handle_request(..., tier="user")
- /admin -> handle_request(..., tier="admin")

-----------------------------------------
STAGE 2 — Add tool policy configuration
-----------------------------------------
Create a single source of truth: broker-service/tool_policy.py

Implement:
- DEFAULT_DENY = True (recommended) OR DEFAULT_ALLOW = True (recommended only if you explicitly list admin-only tools)
- USER_ALLOWED_TOOLS = set([...])  # explicit allowlist
- ADMIN_ALLOWED_TOOLS = None or “ALL”

Recommended approach: explicit user allowlist.
Example placeholders (Kiro: fill with your real tool names):
USER_ALLOWED_TOOLS = {
  # AWS infra read-only basics
  "ecs_call_tool",
  "iac_call_tool",

  # Deployment metrics read-only
  "deploy_get_run",
  "deploy_get_steps",
  "deploy_find_latest",
  "deploy_find_active",
  "deploy_get_summary",

  # PR tools
  "pr_get_diff",
  "pr_summarize",

  # Pricing (safe ones)
  "pricingcalc_estimate_from_cfn"
}

Everything not in USER_ALLOWED_TOOLS is admin-only by default (or denied for /ask).

Add helper:
def is_tool_allowed(tool_name: str, tier: str) -> bool:
  if tier == "admin": return True
  return tool_name in USER_ALLOWED_TOOLS

-----------------------------------------
STAGE 3 — Enforce gating at BOTH critical points (MUST)
-----------------------------------------
A) Before model call (tool advertisement)
- Broker merges tools from MCP endpoints as it already does.
- Filter the tool list based on tier using is_tool_allowed().
- Send only filtered tools to Bedrock.

B) During tool execution (tool_use enforcement)
- When Bedrock returns a tool_use:
  - If tool not allowed for tier: STOP and return error (fail closed)
  - Do not proxy the tool call to any MCP endpoint.
  - Include safe debug: tool name + “not allowed for this endpoint”.

This prevents jailbreak / hallucinated tool calls.

-----------------------------------------
STAGE 4 — Map tools to MCP backends (router table)
-----------------------------------------
In broker add explicit routing for tools -> MCP endpoint URL.

Example:
TOOL_BACKENDS = {
  # existing
  "ecs_call_tool":       ("http://internal-mcp.../call-tool", "ecs"),
  "iac_call_tool":       ("http://internal-mcp.../call-tool", "iac"),

  # metrics endpoint on MCP ALB
  "deploy_*":            ("http://internal-mcp.../metrics", None),

  # pricingcalc endpoint on MCP ALB
  "pricingcalc_*":       ("http://internal-mcp.../pricingcalc", None),

  # PR endpoint on MCP ALB
  "pr_*":                ("http://internal-mcp.../pr", None)
}

Implementation guidance:
- Prefer prefix routing:
  - tool startswith "deploy_" -> /metrics
  - tool startswith "pricingcalc_" -> /pricingcalc
  - tool startswith "pr_" -> /pr
  - ecs_call_tool/iac_call_tool -> existing gateway /call-tool
- Keep existing behavior for current tools; only refactor if needed.

-----------------------------------------
STAGE 5 — Return shaped responses (so callers can tell what happened)
-----------------------------------------
For both endpoints return:
{
  "answer": "...",
  "debug": {
    "tier": "user|admin",
    "tools_advertised_count": N,
    "tools_called": ["..."],
    "denied_tool_calls": ["..."],      # only if attempted
    "mcp_calls_ms": ...,
    "bedrock_call_ms": ...,
    "total_ms": ...
  }
}

Important:
- Do NOT include secrets, tokens, or tool payloads in debug
- It’s fine to include tool names + timing + counts

-----------------------------------------
STAGE 6 — Smoke tests
-----------------------------------------
1) Verify /ask advertises subset
- POST /ask with a prompt that would normally trigger a known admin-only tool
- Confirm broker does NOT include that tool in tools/list sent to model (log count + tool names in debug if you already log them safely)
- Confirm if model attempts it anyway, broker denies it

2) Verify /admin includes all tools
- POST /admin with same prompt
- Confirm tool executes

3) Regression: existing /ask paths still work (ECS/CFN questions)

-----------------------------------------
DELIVERABLES
- Broker exposes POST /ask and POST /admin
- /ask: only approved subset tools are advertised + executable
- /admin: all tools are advertised + executable
- Fail-closed enforcement in both advertisement and execution
- Clear debug showing which tier and what tools were used/denied


