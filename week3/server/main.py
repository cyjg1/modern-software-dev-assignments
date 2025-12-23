from __future__ import annotations

import argparse
import asyncio
import logging
import os
import secrets
from datetime import datetime
from typing import Any, Literal

import httpx
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_FIELDS = "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
DAILY_FIELDS = (
    "weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_probability_max,wind_speed_10m_max"
)

DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 1
MAX_FORECAST_DAYS = 7

UNITS_CONFIG: dict[str, dict[str, str]] = {
    "metric": {},
    "imperial": {
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    },
}

THUNDER_CODES = {95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82}

WMO_CODE_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

logger = logging.getLogger("weather_travel")


class StaticTokenVerifier:
    def __init__(self, token: str, scopes: list[str], resource: str | None) -> None:
        self._token = token
        self._scopes = scopes
        self._resource = resource

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id="api-key",
            scopes=self._scopes,
            expires_at=None,
            resource=self._resource,
        )


def _validate_city(city: str) -> str:
    if not city or not city.strip():
        raise ToolError("City must be a non-empty string.")
    return city.strip()


def _validate_units(units: str) -> Literal["metric", "imperial"]:
    units = units.strip().lower()
    if units not in UNITS_CONFIG:
        raise ToolError("Units must be 'metric' or 'imperial'.")
    return units  # type: ignore[return-value]


def _validate_days(days: int) -> int:
    if days < 1 or days > MAX_FORECAST_DAYS:
        raise ToolError(f"Days must be between 1 and {MAX_FORECAST_DAYS}.")
    return days


def _conditions_from_code(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODE_LABELS.get(code, "Unknown")


def _parse_scopes(raw_scopes: str | None) -> list[str]:
    if not raw_scopes:
        return []
    return [scope.strip() for scope in raw_scopes.split(",") if scope.strip()]


def _normalize_public_url(url: str) -> str:
    normalized = url.rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("Public URL must start with http:// or https://")
    return normalized


def _default_public_url(host: str, port: int) -> str:
    public_host = "127.0.0.1" if host in {"0.0.0.0", "localhost"} else host
    return f"http://{public_host}:{port}"


async def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params)
            except httpx.TimeoutException as exc:
                if attempt < MAX_RETRIES:
                    logger.warning("Timeout contacting %s, retrying.", url)
                    continue
                raise ToolError("Upstream request timed out.") from exc
            except httpx.RequestError as exc:
                raise ToolError(f"Network error contacting upstream API: {exc}") from exc

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "1")
                wait_seconds = int(retry_after) if retry_after.isdigit() else 1
                if attempt < MAX_RETRIES:
                    logger.warning("Rate limited by upstream API; backing off for %s seconds.", wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue
                raise ToolError("Rate limit exceeded. Please try again later.")

            if response.status_code >= 500 and attempt < MAX_RETRIES:
                logger.warning("Upstream server error (%s). Retrying.", response.status_code)
                await asyncio.sleep(1)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ToolError(f"Upstream API error: HTTP {exc.response.status_code}.") from exc

            try:
                return response.json()
            except ValueError as exc:
                raise ToolError("Upstream API returned invalid JSON.") from exc

    raise ToolError("Upstream request failed after retries.")


async def _geocode_city(city: str) -> dict[str, Any]:
    data = await _request_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results") or []
    if not results:
        raise ToolError(f"No locations found for '{city}'. Try a larger nearby city.")
    return results[0]


def _build_location(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": result.get("name"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "country": result.get("country"),
        "admin1": result.get("admin1"),
        "timezone": result.get("timezone"),
    }


async def _fetch_current_weather(
    latitude: float, longitude: float, units: Literal["metric", "imperial"]
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "timezone": "auto",
    }
    params.update(UNITS_CONFIG[units])
    return await _request_json(FORECAST_URL, params)


async def _fetch_daily_forecast(
    latitude: float, longitude: float, units: Literal["metric", "imperial"], days: int
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_FIELDS,
        "forecast_days": days,
        "timezone": "auto",
    }
    params.update(UNITS_CONFIG[units])
    return await _request_json(FORECAST_URL, params)


def _select_forecast_date(dates: list[str], day: str) -> str:
    normalized = day.strip().lower()
    if normalized in {"today", "tomorrow"}:
        index = 0 if normalized == "today" else 1
        if index >= len(dates):
            raise ToolError("Requested day is outside the forecast window.")
        return dates[index]

    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError as exc:
        raise ToolError("day must be 'today', 'tomorrow', or YYYY-MM-DD.") from exc

    if day not in dates:
        raise ToolError("Requested date is outside the forecast window.")
    return day


def _assess_risk(
    precip_prob: int | None, wind_speed: float | None, weather_code: int | None
) -> str:
    if weather_code in THUNDER_CODES:
        return "high"
    if precip_prob is not None and precip_prob >= 70:
        return "high"
    if wind_speed is not None and wind_speed >= 45:
        return "high"
    if weather_code in SNOW_CODES or weather_code in RAIN_CODES:
        return "moderate"
    if precip_prob is not None and precip_prob >= 40:
        return "moderate"
    if wind_speed is not None and wind_speed >= 30:
        return "moderate"
    return "low"


def _temperature_thresholds(units: Literal["metric", "imperial"]) -> tuple[float, float]:
    if units == "imperial":
        return 86.0, 32.0
    return 30.0, 0.0


def _build_auth_settings(host: str, port: int) -> tuple[AuthSettings, StaticTokenVerifier]:
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    if not auth_token:
        raise ValueError("MCP_AUTH_TOKEN must be set when auth is enabled.")

    scopes = _parse_scopes(os.getenv("MCP_AUTH_SCOPES"))
    public_url = os.getenv("MCP_PUBLIC_URL")
    if public_url:
        public_url = _normalize_public_url(public_url)
    else:
        public_url = _default_public_url(host, port)

    issuer_url = _normalize_public_url(os.getenv("MCP_ISSUER_URL", public_url))
    resource_url = _normalize_public_url(os.getenv("MCP_RESOURCE_URL", public_url))

    auth_settings = AuthSettings(
        issuer_url=issuer_url,
        resource_server_url=resource_url,
        required_scopes=scopes or None,
    )
    token_verifier = StaticTokenVerifier(auth_token, scopes, resource_url)
    return auth_settings, token_verifier


def register_tools(server: FastMCP) -> None:
    @server.tool(description="Get current weather conditions for a city using Open-Meteo.")
    async def get_current_weather(
        city: str, units: Literal["metric", "imperial"] = "metric"
    ) -> dict[str, Any]:
        city = _validate_city(city)
        units = _validate_units(units)

        location = await _geocode_city(city)
        forecast = await _fetch_current_weather(
            latitude=location["latitude"], longitude=location["longitude"], units=units
        )

        current = forecast.get("current")
        if not current:
            raise ToolError("No current weather data returned.")

        units_data = forecast.get("current_units", {})
        weather_code = current.get("weather_code")
        return {
            "location": _build_location(location),
            "current": {
                "time": current.get("time"),
                "temperature": current.get("temperature_2m"),
                "apparent_temperature": current.get("apparent_temperature"),
                "precipitation": current.get("precipitation"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": weather_code,
                "conditions": _conditions_from_code(weather_code),
            },
            "units": {
                "temperature": units_data.get("temperature_2m"),
                "apparent_temperature": units_data.get("apparent_temperature"),
                "precipitation": units_data.get("precipitation"),
                "wind_speed": units_data.get("wind_speed_10m"),
            },
        }

    @server.tool(description="Get a multi-day weather forecast for a city using Open-Meteo.")
    async def get_forecast(
        city: str, days: int = 3, units: Literal["metric", "imperial"] = "metric"
    ) -> dict[str, Any]:
        city = _validate_city(city)
        units = _validate_units(units)
        days = _validate_days(days)

        location = await _geocode_city(city)
        forecast = await _fetch_daily_forecast(
            latitude=location["latitude"], longitude=location["longitude"], units=units, days=days
        )

        daily = forecast.get("daily")
        if not daily or not daily.get("time"):
            raise ToolError("No daily forecast data returned.")

        units_data = forecast.get("daily_units", {})
        entries = []
        for date_str, code, t_max, t_min, precip, wind in zip(
            daily.get("time", []),
            daily.get("weather_code", []),
            daily.get("temperature_2m_max", []),
            daily.get("temperature_2m_min", []),
            daily.get("precipitation_probability_max", []),
            daily.get("wind_speed_10m_max", []),
        ):
            entries.append(
                {
                    "date": date_str,
                    "temperature_max": t_max,
                    "temperature_min": t_min,
                    "precipitation_probability": precip,
                    "wind_speed_max": wind,
                    "weather_code": code,
                    "conditions": _conditions_from_code(code),
                }
            )

        return {
            "location": _build_location(location),
            "days": days,
            "daily": entries,
            "units": {
                "temperature_max": units_data.get("temperature_2m_max"),
                "temperature_min": units_data.get("temperature_2m_min"),
                "precipitation_probability": units_data.get("precipitation_probability_max"),
                "wind_speed_max": units_data.get("wind_speed_10m_max"),
            },
        }

    @server.tool(description="Provide travel advice for a city based on the daily forecast.")
    async def get_travel_advice(
        city: str,
        day: str = "today",
        units: Literal["metric", "imperial"] = "metric",
    ) -> dict[str, Any]:
        city = _validate_city(city)
        units = _validate_units(units)

        location = await _geocode_city(city)
        forecast = await _fetch_daily_forecast(
            latitude=location["latitude"],
            longitude=location["longitude"],
            units=units,
            days=MAX_FORECAST_DAYS,
        )

        daily = forecast.get("daily")
        if not daily or not daily.get("time"):
            raise ToolError("No daily forecast data returned.")

        units_data = forecast.get("daily_units", {})
        dates = list(daily.get("time", []))
        selected_date = _select_forecast_date(dates, day)
        index = dates.index(selected_date)

        weather_code = daily.get("weather_code", [None])[index]
        t_max = daily.get("temperature_2m_max", [None])[index]
        t_min = daily.get("temperature_2m_min", [None])[index]
        precip = daily.get("precipitation_probability_max", [None])[index]
        wind = daily.get("wind_speed_10m_max", [None])[index]

        conditions = _conditions_from_code(weather_code)
        risk_level = _assess_risk(precip, wind, weather_code)
        hot_threshold, cold_threshold = _temperature_thresholds(units)

        recommendations: list[str] = []
        if precip is not None and precip >= 40:
            recommendations.append("Pack rain gear or an umbrella.")
        if weather_code in THUNDER_CODES:
            recommendations.append("Thunderstorm risk; keep indoor backup plans.")
        if wind is not None and wind >= 35:
            recommendations.append("Strong winds expected; secure loose items.")
        if t_max is not None and t_max >= hot_threshold:
            recommendations.append("Hot daytime temperatures; stay hydrated.")
        if t_min is not None and t_min <= cold_threshold:
            recommendations.append("Cold mornings/evenings; dress in layers.")
        if not recommendations:
            recommendations.append("Conditions look favorable for travel.")

        temp_unit = units_data.get("temperature_2m_max")
        summary_parts = [conditions]
        if t_max is not None and t_min is not None and temp_unit:
            summary_parts.append(f"High {t_max}{temp_unit} / Low {t_min}{temp_unit}.")
        if precip is not None:
            summary_parts.append(f"Precip chance {precip}%.")
        summary = " ".join(summary_parts).strip()

        return {
            "location": _build_location(location),
            "day": selected_date,
            "summary": summary,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "weather": {
                "temperature_max": t_max,
                "temperature_min": t_min,
                "precipitation_probability": precip,
                "wind_speed_max": wind,
                "weather_code": weather_code,
                "conditions": conditions,
            },
            "units": {
                "temperature_max": units_data.get("temperature_2m_max"),
                "temperature_min": units_data.get("temperature_2m_min"),
                "precipitation_probability": units_data.get("precipitation_probability_max"),
                "wind_speed_max": units_data.get("wind_speed_10m_max"),
            },
        }


def create_server(host: str, port: int, log_level: str) -> FastMCP:
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    auth_settings = None
    token_verifier = None
    if auth_token:
        auth_settings, token_verifier = _build_auth_settings(host, port)

    server = FastMCP(
        "weather-travel",
        instructions=(
            "Use these tools to fetch weather and travel guidance for a city. "
            "Provide clear city names and specify units if needed."
        ),
        host=host,
        port=port,
        log_level=log_level,
        auth=auth_settings,
        token_verifier=token_verifier,
    )
    register_tools(server)
    return server


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weather + Travel MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport to use (http maps to streamable-http)",
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8000")))
    parser.add_argument(
        "--log-level",
        default=os.getenv("MCP_LOG_LEVEL", os.getenv("FASTMCP_LOG_LEVEL", "INFO")),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    log_level = str(args.log_level).upper()
    server = create_server(args.host, args.port, log_level)

    transport = args.transport
    if transport == "http":
        transport = "streamable-http"

    server.run(transport=transport)


if __name__ == "__main__":
    main()
