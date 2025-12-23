# Week 3 - Weather + Travel MCP Server

This MCP server wraps the Open-Meteo geocoding and forecast APIs to provide
current weather, multi-day forecasts, and simple travel advice. It runs locally
over STDIO or as a remote HTTP server (streamable-http).

## External APIs used
- https://geocoding-api.open-meteo.com/v1/search
- https://api.open-meteo.com/v1/forecast

## Tools
### get_current_weather
Get current weather conditions for a city.
- Params:
  - `city` (string, required)
  - `units` ("metric" or "imperial", optional, default: "metric")

### get_forecast
Get a multi-day forecast.
- Params:
  - `city` (string, required)
  - `days` (int, optional, 1-7, default: 3)
  - `units` ("metric" or "imperial", optional, default: "metric")

### get_travel_advice
Provide travel guidance based on the daily forecast.
- Params:
  - `city` (string, required)
  - `day` ("today", "tomorrow", or YYYY-MM-DD, optional, default: "today")
  - `units` ("metric" or "imperial", optional, default: "metric")

## Setup (local STDIO)
From the repository root:
```bash
cd modern-software-dev-assignments/week3/server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional: set log level with `MCP_LOG_LEVEL=DEBUG` (or `FASTMCP_LOG_LEVEL=DEBUG`).

## Run (local STDIO)
```bash
python main.py
```

## Run (HTTP remote mode)
```bash
python main.py --transport http --host 0.0.0.0 --port 8000
```

The streamable HTTP endpoint is:
```
http://<host>:<port>/mcp
```

## MCP client configuration (Claude Desktop example)
Add this to your Claude Desktop config:
```json
{
  "mcpServers": {
    "weather-travel": {
      "command": "python",
      "args": [
        "D:\\\\program\\\\cyjg\\\\modern-software-dev-assignments\\\\week3\\\\server\\\\main.py"
      ],
      "cwd": "D:\\\\program\\\\cyjg\\\\modern-software-dev-assignments\\\\week3\\\\server"
    }
  }
}
```

## HTTP authentication (optional API key)
Set an API key and require it for HTTP mode:
```bash
set MCP_AUTH_TOKEN=your-secret-key
python main.py --transport http --host 0.0.0.0 --port 8000
```

Clients must send:
```
Authorization: Bearer your-secret-key
```

Optional auth-related env vars:
- `MCP_PUBLIC_URL` (defaults to http://127.0.0.1:<port>)
- `MCP_ISSUER_URL` and `MCP_RESOURCE_URL` (override auth metadata URLs)
- `MCP_AUTH_SCOPES` (comma-separated, optional)

## Example invocation flow
1. Start Claude Desktop after adding the MCP config.
2. Ask: "Use get_current_weather for Tokyo."
3. Ask: "Get a 5-day forecast for Berlin."
4. Ask: "Give me travel advice for Paris tomorrow."

## Notes on reliability
- Handles HTTP timeouts and upstream errors with clear messages.
- Backs off once on rate limits (HTTP 429) and retries once on 5xx errors.
