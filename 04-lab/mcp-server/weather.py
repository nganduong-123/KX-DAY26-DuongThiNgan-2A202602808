from typing import Any
import asyncio
import httpx
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
OPEN_METEO_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "weather-app/1.0"

# Get API key from environment variable
API_KEY = os.getenv("WEATHERAPI_KEY")

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_code_text(code: int) -> str:
    """Translate a WMO weather code returned by Open-Meteo."""
    return WEATHER_CODES.get(code, f"Weather code {code}")


def wind_direction(degrees: float) -> str:
    """Convert degrees into a compact 16-point compass direction."""
    directions = (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    )
    return directions[round(degrees / 22.5) % 16]


async def make_open_meteo_request(city: str) -> dict[str, Any] | None:
    """Fetch live weather without a key when WEATHERAPI_KEY is unavailable."""
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            geo_response = await client.get(
                OPEN_METEO_GEOCODING,
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo_response.raise_for_status()
            locations = geo_response.json().get("results", [])
            if not locations:
                return None

            location = locations[0]
            weather_response = await client.get(
                OPEN_METEO_FORECAST,
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": ",".join((
                        "temperature_2m", "apparent_temperature",
                        "relative_humidity_2m", "weather_code",
                        "wind_speed_10m", "wind_direction_10m",
                        "surface_pressure", "uv_index", "visibility",
                    )),
                    "daily": ",".join((
                        "weather_code", "temperature_2m_max",
                        "temperature_2m_min", "precipitation_probability_max",
                        "wind_speed_10m_max", "uv_index_max",
                    )),
                    "timezone": "auto",
                    "forecast_days": 3,
                },
            )
            weather_response.raise_for_status()
            return {"location": location, "weather": weather_response.json()}
    except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as exc:
        print(f"Open-Meteo fallback error: {exc}")
        return None

async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    # Check if API key is set
    if not API_KEY:
        print("ERROR: WeatherAPI key not set. Please set WEATHERAPI_KEY environment variable.")
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    # Add API key to parameters
    params["key"] = API_KEY
    
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    if not API_KEY:
        fallback = await make_open_meteo_request(city)
        if not fallback:
            return f"Unable to fetch current weather data for {city}."
        location = fallback["location"]
        current = fallback["weather"]["current"]
        visibility_km = current["visibility"] / 1000
        return f"""
Current Weather for {location['name']}, {location.get('admin1', '')}, {location.get('country', '')}:

Temperature: {current['temperature_2m']}°C
Feels like: {current['apparent_temperature']}°C
Condition: {weather_code_text(current['weather_code'])}
Humidity: {current['relative_humidity_2m']}%
Wind: {current['wind_speed_10m']} km/h {wind_direction(current['wind_direction_10m'])}
Pressure: {current['surface_pressure']} hPa
UV Index: {current['uv_index']}
Visibility: {visibility_km:.1f} km

Last updated: {current['time']}
Provider: Open-Meteo (live fallback because WEATHERAPI_KEY is not configured)
"""

    data = await make_weather_request("current.json", params)

    if not data:
        if not API_KEY:
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch current weather data for {city}. Please check the city name and API key configuration."

    current = data["current"]
    location = data["location"]
    
    return f"""
Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    # Limit days to 3 for free tier
    days = min(days, 3)
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    if not API_KEY:
        fallback = await make_open_meteo_request(city)
        if not fallback:
            return f"Unable to fetch forecast data for {city}."
        location = fallback["location"]
        daily = fallback["weather"]["daily"]
        forecasts = [
            f"Weather Forecast for {location['name']}, "
            f"{location.get('admin1', '')}, {location.get('country', '')}:"
        ]
        for index, date in enumerate(daily["time"][:days]):
            forecasts.append(f"""
{date}:
High: {daily['temperature_2m_max'][index]}°C
Low: {daily['temperature_2m_min'][index]}°C
Condition: {weather_code_text(daily['weather_code'][index])}
Chance of Rain: {daily['precipitation_probability_max'][index]}%
Max Wind: {daily['wind_speed_10m_max'][index]} km/h
UV Index: {daily['uv_index_max'][index]}
""")
        forecasts.append("Provider: Open-Meteo (live fallback because WEATHERAPI_KEY is not configured)")
        return "\n---\n".join(forecasts)

    data = await make_weather_request("forecast.json", params)

    if not data:
        if not API_KEY:
            return f"❌ WeatherAPI key not configured. Please set WEATHERAPI_KEY environment variable with your API key from weatherapi.com"
        return f"Unable to fetch forecast data for {city}. Please check the city name and API key configuration."

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""
{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Ready to provide weather data for Australian cities and worldwide."

print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")
if not API_KEY:
    print("ℹ️  WEATHERAPI_KEY is not set; using live Open-Meteo fallback")

if __name__ == "__main__":
    import sys
    
    is_cloud_run = bool(os.getenv("PORT"))
    is_standalone = len(sys.argv) == 1 and sys.stdin.isatty()
    
    if is_cloud_run or is_standalone:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run()
