import pytest
import sqlite3
import time
import json
from unittest.mock import patch, MagicMock
from weather_cli import db
from pathlib import Path

SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB = {"city": "TestDBville", "temp": 21.5, "description": "db_sunny", "temp_unit": "°C", "speed_unit": "m/s"}
SAMPLE_VALID_FORECAST_PARSED_DB = [{"date": "2025-05-15 (DbThursday)", "temp_min": 18.0, "temp_max": 25.0, "description": "db_clear_sky", "temp_unit": "°C"}]
ANOTHER_VALID_CURRENT_WEATHER_PARSED_DB = {"city": "NewTestDBville", "temp": 10.0, "description": "db_cloudy", "temp_unit": "°F", "speed_unit": "mph"}
ANOTHER_VALID_FORECAST_PARSED_DB = [{"date": "2025-05-16 (DbFriday)", "temp_min": 5.0, "temp_max": 15.0, "description": "db_overcast", "temp_unit": "°F"}]


@pytest.fixture
def temporary_db_file_path(tmp_path: Path) -> str:
    db_file = tmp_path / "test_weather_cache.db"
    return str(db_file)

@pytest.fixture
def patched_db_module(temporary_db_file_path: str):
    original_db_name = db.DB_NAME
    db.DB_NAME = temporary_db_file_path
    db.init_db()
    yield db
    db.DB_NAME = original_db_name


class TestDatabaseInitialization:
    def test_init_db_creates_table_and_is_idempotent(self, temporary_db_file_path: str):
        with patch.object(db, 'DB_NAME', temporary_db_file_path):
            db.init_db()
            conn_first_init = sqlite3.connect(temporary_db_file_path)
            cursor_first = conn_first_init.cursor()
            cursor_first.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_cache';")
            assert cursor_first.fetchone() is not None
            conn_first_init.close()

            db.init_db()
            conn_second_init = sqlite3.connect(temporary_db_file_path)
            cursor_second = conn_second_init.cursor()
            cursor_second.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_cache';")
            assert cursor_second.fetchone() is not None
            conn_second_init.close()

    def test_get_db_connection_sets_row_factory(self, patched_db_module):
        conn = patched_db_module.get_db_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestCacheWeatherOperation:
    def test_cache_new_data_is_stored_correctly(self, patched_db_module):
        cache_key = "new_data_metric"
        patched_db_module.cache_weather(cache_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)

        conn = patched_db_module.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_weather_data, forecast_data, timestamp FROM weather_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert json.loads(row["current_weather_data"]) == SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB
        assert json.loads(row["forecast_data"]) == SAMPLE_VALID_FORECAST_PARSED_DB
        assert isinstance(row["timestamp"], int)
        assert row["timestamp"] <= int(time.time())
        assert row["timestamp"] > int(time.time()) - 5

    def test_cache_weather_replaces_existing_data(self, patched_db_module):
        cache_key = "replace_data_metric"
        patched_db_module.cache_weather(cache_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)
        patched_db_module.cache_weather(cache_key, ANOTHER_VALID_CURRENT_WEATHER_PARSED_DB, ANOTHER_VALID_FORECAST_PARSED_DB)

        retrieved = patched_db_module.get_cached_weather(cache_key)
        assert retrieved is not None
        assert retrieved["current"] == ANOTHER_VALID_CURRENT_WEATHER_PARSED_DB
        assert retrieved["forecast"] == ANOTHER_VALID_FORECAST_PARSED_DB

    @pytest.mark.parametrize("current_data, forecast_data", [
        (None, SAMPLE_VALID_FORECAST_PARSED_DB),
        (SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, None),
        (None, None),
        ({}, SAMPLE_VALID_FORECAST_PARSED_DB),
        (SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, []),
    ])
    def test_cache_weather_skips_incomplete_data(self, patched_db_module, current_data, forecast_data):
        cache_key = "incomplete_data_metric"
        patched_db_module.cache_weather(cache_key, current_data, forecast_data)
        retrieved = patched_db_module.get_cached_weather(cache_key)
        assert retrieved is None

    def test_cache_weather_handles_sqlite_error_on_write(self, temporary_db_file_path, mocker, capsys):
        with patch.object(db, 'DB_NAME', temporary_db_file_path):
            db.init_db()
            cache_key = "sqlite_error_write_metric"
            simulated_error_message = "Simulated database write failure"
            
            mock_execute = mocker.MagicMock(side_effect=sqlite3.Error(simulated_error_message))
            mock_cursor_instance = MagicMock()
            mock_cursor_instance.execute = mock_execute
            mock_connection = MagicMock()
            mock_connection.cursor.return_value = mock_cursor_instance
            
            with patch.object(db, 'get_db_connection', return_value=mock_connection):
                db.cache_weather(cache_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)
        
            captured = capsys.readouterr()
            # Check for key parts of the message
            assert "Database error during caching for key" in captured.out
            assert cache_key in captured.out
            assert simulated_error_message in captured.out
            
            retrieved = db.get_cached_weather(cache_key)
            assert retrieved is None


class TestGetCachedWeatherOperation:
    def test_get_valid_and_fresh_cached_data(self, patched_db_module):
        cache_key = "get_fresh_metric"
        current_time_val = int(time.time())
        with patch.object(time, 'time', return_value=current_time_val):
             patched_db_module.cache_weather(cache_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)

        retrieved = patched_db_module.get_cached_weather(cache_key)
        
        assert retrieved is not None
        assert retrieved["current"] == SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB
        assert retrieved["forecast"] == SAMPLE_VALID_FORECAST_PARSED_DB

    def test_get_cached_data_returns_none_if_timestamp_is_expired(self, patched_db_module):
        cache_key = "get_expired_metric"
        current_simulated_time = int(time.time())
        expired_timestamp = current_simulated_time - patched_db_module.CACHE_DURATION_SECONDS * 2

        conn = patched_db_module.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weather_cache (cache_key, current_weather_data, forecast_data, timestamp) VALUES (?, ?, ?, ?)",
            (cache_key, json.dumps(SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB), json.dumps(SAMPLE_VALID_FORECAST_PARSED_DB), expired_timestamp)
        )
        conn.commit()
        conn.close()
        
        with patch.object(time, 'time', return_value=current_simulated_time):
            retrieved = patched_db_module.get_cached_weather(cache_key)
        assert retrieved is None

    def test_get_cached_data_returns_none_for_key_not_in_cache(self, patched_db_module):
        retrieved = patched_db_module.get_cached_weather("unseen_key_metric")
        assert retrieved is None

    @pytest.mark.parametrize("bad_current_json, bad_forecast_json", [
        ("not valid json", json.dumps(SAMPLE_VALID_FORECAST_PARSED_DB)),
        (json.dumps(SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB), "not valid json at all"),
    ])
    def test_get_cached_data_handles_malformed_json_in_db(self, patched_db_module, capsys, bad_current_json, bad_forecast_json):
        cache_key = "malformed_json_metric"
        fresh_timestamp = int(time.time()) - 10

        conn = patched_db_module.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weather_cache (cache_key, current_weather_data, forecast_data, timestamp) VALUES (?, ?, ?, ?)",
            (cache_key, bad_current_json, bad_forecast_json, fresh_timestamp)
        )
        conn.commit()
        conn.close()

        retrieved = patched_db_module.get_cached_weather(cache_key)
        assert retrieved is None
        captured = capsys.readouterr()
        # Check for key parts of the message
        assert "Warning: Could not decode cached JSON data for key" in captured.out
        assert cache_key in captured.out

    @pytest.mark.parametrize("db_current_data, db_forecast_data", [
        (None, json.dumps(SAMPLE_VALID_FORECAST_PARSED_DB)),
        (json.dumps(SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB), None),
    ])
    def test_get_cached_data_handles_null_data_fields_in_db(self, patched_db_module, db_current_data, db_forecast_data):
        cache_key = "null_field_metric"
        fresh_timestamp = int(time.time()) - 10
        conn = patched_db_module.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weather_cache (cache_key, current_weather_data, forecast_data, timestamp) VALUES (?, ?, ?, ?)",
            (cache_key, db_current_data, db_forecast_data, fresh_timestamp)
        )
        conn.commit()
        conn.close()
        retrieved = patched_db_module.get_cached_weather(cache_key)
        assert retrieved is None


class TestClearCacheOperations:
    def test_clear_cache_for_city_removes_all_unit_versions(self, patched_db_module, capsys):
        city = "ClearMyCity"
        metric_key = f"{city.lower()}_metric"
        imperial_key = f"{city.lower()}_imperial"
        unrelated_key = "othercity_metric"

        patched_db_module.cache_weather(metric_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)
        patched_db_module.cache_weather(imperial_key, ANOTHER_VALID_CURRENT_WEATHER_PARSED_DB, ANOTHER_VALID_FORECAST_PARSED_DB)
        patched_db_module.cache_weather(unrelated_key, SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)

        patched_db_module.clear_cache_for_city(city)

        assert patched_db_module.get_cached_weather(metric_key) is None
        assert patched_db_module.get_cached_weather(imperial_key) is None
        assert patched_db_module.get_cached_weather(unrelated_key) is not None
        captured = capsys.readouterr()
        assert f"Cache cleared for {city} (all unit versions)." in captured.out

    def test_clear_cache_for_city_when_no_entries_exist(self, patched_db_module, capsys):
        city_no_cache = "NoCacheCity"
        patched_db_module.clear_cache_for_city(city_no_cache)
        captured = capsys.readouterr()
        assert f"No cache entry found for {city_no_cache}." in captured.out

    def test_clear_all_cache_removes_all_entries(self, patched_db_module, capsys):
        patched_db_module.cache_weather("any_city_metric", SAMPLE_VALID_CURRENT_WEATHER_PARSED_DB, SAMPLE_VALID_FORECAST_PARSED_DB)
        patched_db_module.cache_weather("another_city_imperial", ANOTHER_VALID_CURRENT_WEATHER_PARSED_DB, ANOTHER_VALID_FORECAST_PARSED_DB)
        
        patched_db_module.clear_all_cache()

        assert patched_db_module.get_cached_weather("any_city_metric") is None
        assert patched_db_module.get_cached_weather("another_city_imperial") is None
        captured = capsys.readouterr()
        assert "All weather cache cleared." in captured.out

    def test_clear_all_cache_on_an_already_empty_cache(self, patched_db_module, capsys):
        patched_db_module.clear_all_cache() 
        captured = capsys.readouterr()
        assert "All weather cache cleared." in captured.out

    @pytest.mark.parametrize("clear_function_name, clear_function_args_tuple", [
        ("clear_cache_for_city", ("ErrorCity",)),
        ("clear_all_cache", ()),
    ])
    def test_clear_cache_functions_handle_sqlite_error(self, temporary_db_file_path, mocker, capsys, clear_function_name, clear_function_args_tuple):
        with patch.object(db, 'DB_NAME', temporary_db_file_path):
            db.init_db()
            simulated_error_message = "Simulated database delete failure"
            mock_execute = MagicMock(side_effect=sqlite3.Error(simulated_error_message))
            mock_cursor_instance = MagicMock()
            mock_cursor_instance.execute = mock_execute
            mock_connection = MagicMock()
            mock_connection.cursor.return_value = mock_cursor_instance

            with patch.object(db, 'get_db_connection', return_value=mock_connection):
                clear_function_under_test = getattr(db, clear_function_name)
                clear_function_under_test(*clear_function_args_tuple)
            
            captured = capsys.readouterr()
            assert "Database error while clearing" in captured.out
            if clear_function_args_tuple: # For clear_cache_for_city
                assert clear_function_args_tuple[0] in captured.out
            assert simulated_error_message in captured.out