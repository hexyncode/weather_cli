import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from . import weather_api
from . import db

WEATHER_ICONS = {
    "01d": "☀️", "01n": "🌙", "02d": "🌤️", "02n": "☁️🌙", "03d": "☁️", "03n": "☁️",
    "04d": "🌥️", "04n": "🌥️", "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️🌙",
    "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️", "50d": "🌫️", "50n": "🌫️",
    "unknown": "❓"
}

def get_weather_icon(icon_code: str) -> str:
    return WEATHER_ICONS.get(icon_code, WEATHER_ICONS["unknown"])

def display_current_weather(console: Console, weather_data: dict):
    if not weather_data or not isinstance(weather_data, dict):
        console.print("[bold red]No valid current weather data to display.[/bold red]")
        return

    city = weather_data.get("city", "N/A")
    country = weather_data.get("country", "N/A")
    temp = weather_data.get("temp", "N/A")
    feels_like = weather_data.get("feels_like", "N/A")
    description = weather_data.get("description", "N/A")
    humidity = weather_data.get("humidity", "N/A")
    wind_speed = weather_data.get("wind_speed", "N/A")
    icon_code = weather_data.get("icon", "")
    sunrise = weather_data.get("sunrise", "N/A")
    sunset = weather_data.get("sunset", "N/A")
    weather_icon = get_weather_icon(icon_code)
    
    temp_unit_symbol = weather_data.get("temp_unit", "")
    speed_unit_symbol = weather_data.get("speed_unit", "")

    title = f"[bold cyan]Current Weather in {city}, {country} {weather_icon}[/bold cyan]"
    
    content = Text()
    content.append(f"Temperature: ", style="bold yellow")
    content.append(f"{temp}{temp_unit_symbol} (Feels like: {feels_like}{temp_unit_symbol})\n")
    content.append(f"Condition: ", style="bold yellow")
    content.append(f"{description}\n")
    content.append(f"Humidity: ", style="bold yellow")
    content.append(f"{humidity}%\n")
    content.append(f"Wind: ", style="bold yellow")
    content.append(f"{wind_speed} {speed_unit_symbol}\n")
    content.append(f"Sunrise: ", style="bold yellow")
    content.append(f"{sunrise}\n")
    content.append(f"Sunset: ", style="bold yellow")
    content.append(f"{sunset}")

    console.print(Panel(content, title=title, border_style="blue", expand=False))

def display_forecast(console: Console, forecast_data: list):
    if not forecast_data or not isinstance(forecast_data, list):
        console.print("[bold red]No valid forecast data to display.[/bold red]")
        return

    temp_unit_display = forecast_data[0].get("temp_unit", "") if forecast_data and isinstance(forecast_data[0], dict) else ""

    table = Table(title="[bold cyan]5-Day Weather Forecast[/bold cyan]", show_header=True, header_style="bold magenta")
    table.add_column("Date", style="dim", width=20)
    table.add_column("Condition", width=25)
    table.add_column(f"Temp (Min/Max) {temp_unit_display}", justify="right")
    table.add_column("Icon", justify="center")

    for day_forecast in forecast_data:
        if not isinstance(day_forecast, dict): continue

        date_str = day_forecast.get("date", "N/A")
        description = day_forecast.get("description", "N/A")
        temp_min = day_forecast.get("temp_min", "N/A")
        temp_max = day_forecast.get("temp_max", "N/A")
        icon_code = day_forecast.get("icon", "")
        weather_icon = get_weather_icon(icon_code)
        
        table.add_row(
            date_str,
            description,
            f"{temp_min}{temp_unit_display} / {temp_max}{temp_unit_display}",
            weather_icon
        )
    console.print(table)

def run_cli():
    parser = argparse.ArgumentParser(description="Get current weather and 5-day forecast for a city.")
    parser.add_argument("city", type=str, help="Name of the city to get weather for.")
    
    unit_group = parser.add_mutually_exclusive_group()
    unit_group.add_argument("--metric", action="store_const", dest="units", const="metric", help="Use Metric units (Celsius, m/s). This is the default.")
    unit_group.add_argument("--imperial", action="store_const", dest="units", const="imperial", help="Use Imperial units (Fahrenheit, mph).")
    parser.set_defaults(units="metric")

    parser.add_argument("--no-cache", action="store_true", help="Force fetch fresh data from API, ignoring cache.")
    parser.add_argument("--clear-cache", metavar="CITY_NAME_OR_ALL", type=str, nargs='?', const="ALL", help="Clear cache for a specific city or 'ALL' for the entire cache. Does not fetch new weather.")

    args = parser.parse_args()
    city_name = args.city
    chosen_units = args.units
    use_cache = not args.no_cache
    console = Console()

    if weather_api.API_KEY is None:
        console.print("[bold red]Application critical error: API key (OPENWEATHERMAP_API_KEY) is not configured. Please check your .env file.[/bold red]")
        return

    if args.clear_cache:
        target_to_clear = args.clear_cache
        if target_to_clear.upper() == "ALL":
            db.clear_all_cache()
        else:
            db.clear_cache_for_city(target_to_clear)
        return

    cache_key = f"{city_name.lower()}_{chosen_units}"
    current_weather_parsed = None
    forecast_parsed = None

    if use_cache:
        console.print(f"Checking cache for [cyan]{city_name}[/cyan] (Units: [green]{chosen_units}[/green])...")
        cached_data = db.get_cached_weather(cache_key)
        if cached_data:
            console.print(f"[green]Cache hit for {city_name} ({chosen_units})! Displaying cached data.[/green]")
            current_weather_parsed = cached_data.get("current")
            forecast_parsed = cached_data.get("forecast")
        else:
            console.print(f"[yellow]Cache miss or expired for {city_name} ({chosen_units}).[/yellow]")

    if not current_weather_parsed or not forecast_parsed: 
        with Live(console=console, refresh_per_second=10, transient=True) as live:
            live.update(f"Fetching weather data for [bold blue]{city_name}[/bold blue] (Units: {chosen_units})...")
            
            current_weather_raw = weather_api.get_weather_data(city_name, units=chosen_units)
            if not current_weather_raw:
                live.update(f"[bold red]Failed to retrieve current weather for {city_name}. Check API error messages above.[/bold red]")
                current_weather_parsed = None
                forecast_parsed = None

            
            forecast_raw = None 
            if current_weather_raw: 
                forecast_raw = weather_api.get_forecast_data(city_name, units=chosen_units)
                if not forecast_raw:
                    live.update(f"[bold red]Failed to retrieve forecast for {city_name}. Current weather might be available.[/bold red]")

            if current_weather_raw:
                current_weather_parsed = weather_api.parse_current_weather(current_weather_raw, units=chosen_units)
            else: 
                current_weather_parsed = None 

            if forecast_raw:
                forecast_parsed = weather_api.parse_forecast(forecast_raw, units=chosen_units)
            else: 
                forecast_parsed = None

            if current_weather_parsed and forecast_parsed:
                db.cache_weather(cache_key, current_weather_parsed, forecast_parsed)
                live.update(f"[green]Successfully fetched, parsed, and cached data for {city_name}.[/green]")
            else:
                live.update(f"[bold red]Failed to process or parse complete weather data for {city_name}. Data will not be cached.[/bold red]")
                if not current_weather_parsed:
                    forecast_parsed = None

    # Display logic
    if current_weather_parsed:
        display_current_weather(console, current_weather_parsed)
    else:
        console.print(f"[yellow]Current weather data for {city_name} is unavailable or could not be processed.[/yellow]")

    if forecast_parsed:
        display_forecast(console, forecast_parsed)
    else:
        console.print(f"[yellow]5-day forecast data for {city_name} is unavailable or could not be processed.[/yellow]")

if __name__ == '__main__':
    run_cli()