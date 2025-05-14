import sqlite3
import json
import time
from typing import Optional, Dict, Any, List

DB_NAME = "weather_cache.db"
CACHE_DURATION_SECONDS = 1800

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_cache (
                cache_key TEXT PRIMARY KEY,
                current_weather_data TEXT,
                forecast_data TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"[bold red]Database error during init: {e}[/bold red]")
    finally:
        conn.close()

def get_cached_weather(cache_key: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT current_weather_data, forecast_data, timestamp FROM weather_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[bold red]Database error during cache retrieval for {cache_key}: {e}[/bold red]")
        conn.close()
        return None
    
    conn.close()

    if row:
        current_weather_data_json = row["current_weather_data"]
        forecast_data_json = row["forecast_data"]
        timestamp = row["timestamp"]
        
        if not isinstance(timestamp, int) or (time.time() - timestamp >= CACHE_DURATION_SECONDS):
            return None

        try:
            current_weather = json.loads(current_weather_data_json) if current_weather_data_json is not None else None
            forecast = json.loads(forecast_data_json) if forecast_data_json is not None else None
            if current_weather and forecast:
                return {"current": current_weather, "forecast": forecast}
            else:
                return None 
        except json.JSONDecodeError:
            print(f"[yellow]Warning: Could not decode cached JSON data for key '{cache_key}'.[/yellow]")
            return None
    return None

def cache_weather(cache_key: str, current_weather_data: Optional[Dict[str, Any]], forecast_data: Optional[List[Dict[str, Any]]]) -> None:
    if not current_weather_data or not forecast_data:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        current_weather_json = json.dumps(current_weather_data)
        forecast_json = json.dumps(forecast_data)
        
        cursor.execute("""
            INSERT OR REPLACE INTO weather_cache (cache_key, current_weather_data, forecast_data, timestamp)
            VALUES (?, ?, ?, ?)
        """, (cache_key, current_weather_json, forecast_json, int(time.time())))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[bold red]Database error during caching for key '{cache_key}': {e}[/bold red]")
    except TypeError as te:
        print(f"[bold red]Serialization error during caching for key '{cache_key}': {te}[/bold red]")
    finally:
        conn.close()

def clear_cache_for_city(city_name: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    deleted_rows_count = 0
    city_lower = city_name.lower()
    keys_to_delete = [f"{city_lower}_metric", f"{city_lower}_imperial"]

    try:
        for key in keys_to_delete:
            cursor.execute("DELETE FROM weather_cache WHERE cache_key = ?", (key,))
            deleted_rows_count += cursor.rowcount
        conn.commit()

        if deleted_rows_count > 0:
            print(f"[green]Cache cleared for {city_name} (all unit versions).[/green]")
        else:
            print(f"[yellow]No cache entry found for {city_name}.[/yellow]")
    except sqlite3.Error as e:
        print(f"[bold red]Database error while clearing cache for {city_name}: {e}[/bold red]")
    finally:
        conn.close()

def clear_all_cache() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM weather_cache")
        conn.commit()
        if cursor.rowcount >= 0:
            print("[green]All weather cache cleared.[/green]")
    except sqlite3.Error as e:
        print(f"[bold red]Database error while clearing all cache: {e}[/bold red]")
    finally:
        conn.close()

if __name__ != '__main__':
    init_db()