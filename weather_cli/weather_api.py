import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

load_dotenv()
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

BASE_URL = "http://api.openweathermap.org/data/2.5/"

def get_weather_data(city_name: str, units: str = "metric") -> Optional[Dict[str, Any]]:
    if not API_KEY:
        print("[bold red]API key is not configured. Cannot fetch current weather.[/bold red]")
        return None

    params = {"q": city_name, "appid": API_KEY, "units": units}
    try:
        response = requests.get(f"{BASE_URL}weather", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            print(f"[bold red]Error 401: Invalid API key. Please check your configuration.[/bold red]")
        elif response.status_code == 404:
            print(f"[bold red]Error 404: City '{city_name}' not found. Please check the spelling.[/bold red]")
        else:
            print(f"[bold red]HTTP error occurred while fetching current weather: {http_err} - {response.text if response else 'No response text'}[/bold red]")
    except requests.exceptions.Timeout:
        print(f"[bold red]Error: Request timed out while fetching current weather for {city_name}.[/bold red]")
    except requests.exceptions.RequestException as req_err:
        print(f"[bold red]Error fetching current weather: {req_err}[/bold red]")
    except json.JSONDecodeError as json_err:
        print(f"[bold red]Error decoding JSON response for current weather: {json_err}. Response text: {response.text if response else 'No response available'}[/bold red]")
    return None

def get_forecast_data(city_name: str, units: str = "metric") -> Optional[Dict[str, Any]]:
    if not API_KEY:
        print("[bold red]API key is not configured. Cannot fetch forecast.[/bold red]")
        return None

    params = {"q": city_name, "appid": API_KEY, "units": units}
    try:
        response = requests.get(f"{BASE_URL}forecast", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"[bold red]Error 404: City '{city_name}' not found for forecast. (Or API issue for forecast endpoint)[/bold red]")
        elif response.status_code == 401:
            print(f"[bold red]Error 401: Invalid API key for forecast. Please check your configuration.[/bold red]")
        else:
            print(f"[bold red]HTTP error occurred while fetching forecast: {http_err} - {response.text if response else 'No response text'}[/bold red]")
    except requests.exceptions.Timeout:
        print(f"[bold red]Error: Request timed out while fetching forecast for {city_name}.[/bold red]")
    except requests.exceptions.RequestException as req_err:
        print(f"[bold red]Error fetching forecast: {req_err}[/bold red]")
    except json.JSONDecodeError as json_err:
        print(f"[bold red]Error decoding JSON response for forecast: {json_err}. Response text: {response.text if response else 'No response available'}[/bold red]")
    return None

def parse_current_weather(data: Dict[str, Any], units: str = "metric") -> Dict[str, Any]:
    if not data:
        return {}

    parsed_data = {}
    warnings = []

    temp_unit_symbol = "°C" if units == "metric" else "°F"
    speed_unit_symbol = "m/s" if units == "metric" else "mph"

    parsed_data["city"] = data.get("name", "N/A")
    
    sys_data = data.get("sys", {})
    if not isinstance(sys_data, dict):
        sys_data = {}
        warnings.append("sys data is malformed")
    parsed_data["country"] = sys_data.get("country", "N/A")
    
    sunrise_ts = sys_data.get("sunrise")
    if isinstance(sunrise_ts, (int, float)):
        parsed_data["sunrise"] = datetime.fromtimestamp(sunrise_ts, timezone.utc).strftime('%H:%M:%S UTC')
    else:
        parsed_data["sunrise"] = datetime.fromtimestamp(0, timezone.utc).strftime('%H:%M:%S UTC')
        if sunrise_ts is not None: warnings.append("sunrise timestamp malformed")

    sunset_ts = sys_data.get("sunset")
    if isinstance(sunset_ts, (int, float)):
        parsed_data["sunset"] = datetime.fromtimestamp(sunset_ts, timezone.utc).strftime('%H:%M:%S UTC')
    else:
        parsed_data["sunset"] = datetime.fromtimestamp(0, timezone.utc).strftime('%H:%M:%S UTC')
        if sunset_ts is not None: warnings.append("sunset timestamp malformed")

    main_data = data.get("main", {})
    if not isinstance(main_data, dict):
        main_data = {}
        warnings.append("main weather data is malformed")

    for key in ["temp", "feels_like", "humidity", "temp_min", "temp_max", "pressure"]:
        val = main_data.get(key)
        parsed_data[key] = val if isinstance(val, (int, float)) else "N/A"
        if val is not None and not isinstance(val, (int, float)):
            warnings.append(f"main.{key} data is malformed")

    weather_list = data.get("weather", [])
    if isinstance(weather_list, list) and weather_list:
        weather_info = weather_list[0]
        if isinstance(weather_info, dict):
            raw_desc = weather_info.get("description")
            parsed_data["description"] = raw_desc.capitalize() if isinstance(raw_desc, str) and raw_desc else "N/A"
            if raw_desc == "N/A": # Ensure "N/A" is not changed by capitalize()
                 parsed_data["description"] = "N/A"
            elif not isinstance(raw_desc, str) and raw_desc is not None:
                 warnings.append("weather description is malformed")
            
            raw_icon = weather_info.get("icon")
            parsed_data["icon"] = raw_icon if isinstance(raw_icon, str) else ""
            if not isinstance(raw_icon, str) and raw_icon is not None:
                 warnings.append("weather icon is malformed")
        else:
            warnings.append("weather item is malformed")
            parsed_data["description"] = "N/A"
            parsed_data["icon"] = ""
    else:
        if weather_list is not None and not isinstance(weather_list, list):
            warnings.append("weather data is malformed (not a list)")
        parsed_data["description"] = "N/A"
        parsed_data["icon"] = ""
        if not weather_list:
            warnings.append("weather data list is missing or empty")


    wind_data = data.get("wind", {})
    if not isinstance(wind_data, dict):
        wind_data = {}
        warnings.append("wind data is malformed")
    
    wind_speed_val = wind_data.get("speed")
    parsed_data["wind_speed"] = wind_speed_val if isinstance(wind_speed_val, (int, float)) else "N/A"
    if wind_speed_val is not None and not isinstance(wind_speed_val, (int, float)):
        warnings.append("wind.speed data is malformed")

    wind_deg_val = wind_data.get("deg")
    parsed_data["wind_deg"] = wind_deg_val if isinstance(wind_deg_val, (int, float)) else "N/A"
    if wind_deg_val is not None and not isinstance(wind_deg_val, (int, float)):
        warnings.append("wind.deg data is malformed")

    parsed_data["temp_unit"] = temp_unit_symbol
    parsed_data["speed_unit"] = speed_unit_symbol

    if warnings:
        print(f"[yellow]Warning: Could not parse some current weather details: {'; '.join(warnings)}[/yellow]")

    return parsed_data


def parse_forecast(data: Dict[str, Any], units: str = "metric") -> List[Dict[str, Any]]:
    if not data or not isinstance(data.get("list"), list):
        if data and not isinstance(data.get("list"), list) and data.get("list") is not None:
             print(f"[yellow]Warning: Forecast data 'list' is malformed or missing.[/yellow]")
        return []

    temp_unit_symbol = "°C" if units == "metric" else "°F"
    daily_forecasts_agg = {}
    
    for item_idx, item in enumerate(data["list"]):
        if not isinstance(item, dict):
            print(f"[yellow]Warning: Forecast item #{item_idx} is malformed (not a dict), skipping.[/yellow]")
            continue
            
        try:
            dt_txt = item.get("dt_txt")
            if not isinstance(dt_txt, str):
                raise ValueError("dt_txt is missing or not a string")
            
            dt_txt = item.get("dt_txt")
        
            date_obj_naive = datetime.strptime(dt_txt, '%Y-%m-%d %H:%M:%S')
            date_obj_utc_aware = date_obj_naive.replace(tzinfo=timezone.utc)
            day_str = date_obj_utc_aware.strftime('%Y-%m-%d (%A)')

            if day_str not in daily_forecasts_agg:
                daily_forecasts_agg[day_str] = {
                    "temps": [],
                    "weather_conditions_texts": [],
                    "icons_codes": [],
                    "temp_unit": temp_unit_symbol
                }
            
            main_data = item.get("main", {})
            if not isinstance(main_data, dict):
                raise ValueError("item.main is malformed")
            
            temp_val = main_data.get("temp")
            if not isinstance(temp_val, (int, float)):
                raise ValueError("item.main.temp is malformed or missing")
            daily_forecasts_agg[day_str]["temps"].append(temp_val)

            weather_list = item.get("weather", [])
            if not isinstance(weather_list, list) or not weather_list:
                raise ValueError("item.weather is malformed or empty")
            
            weather_info = weather_list[0]
            if not isinstance(weather_info, dict):
                raise ValueError("item.weather[0] is malformed")

            description = weather_info.get("description")
            icon = weather_info.get("icon")

            if not isinstance(description, str) or not description:
                raise ValueError("item.weather[0].description is malformed or missing")
            if not isinstance(icon, str) or not icon:
                raise ValueError("item.weather[0].icon is malformed or missing")

            daily_forecasts_agg[day_str]["weather_conditions_texts"].append(description)
            daily_forecasts_agg[day_str]["icons_codes"].append(icon)

        except (ValueError, KeyError, TypeError) as e:
            error_time_ref = dt_txt if 'dt_txt' in locals() and isinstance(dt_txt, str) else f'item index {item_idx}'
            print(f"[yellow]Warning: Could not parse some forecast details for item at {error_time_ref}: {e}, skipping item parts for this entry.[/yellow]")
            continue

    parsed_forecast_list = []
    for day_key, details in sorted(daily_forecasts_agg.items()):
        if not details["temps"]:
            continue
        
        day_description = "N/A"
        if details["weather_conditions_texts"]:
            raw_desc = max(set(details["weather_conditions_texts"]), key=details["weather_conditions_texts"].count)
            day_description = raw_desc.capitalize() if raw_desc and raw_desc != "N/A" else "N/A"
            if raw_desc == "N/A": day_description = "N/A"


        day_icon = ""
        if details["icons_codes"]:
            day_icon = max(set(details["icons_codes"]), key=details["icons_codes"].count)

        parsed_forecast_list.append({
            "date": day_key,
            "temp_min": min(details["temps"]),
            "temp_max": max(details["temps"]),
            "description": day_description,
            "icon": day_icon,
            "temp_unit": details["temp_unit"]
        })
    
    return parsed_forecast_list[:5]