import pytest
import argparse
from unittest.mock import patch, MagicMock, call, ANY
from rich.text import Text # Import for type checking
from weather_cli import cli, db, weather_api # weather_api needed for patching its API_KEY

SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI = {"city": "CliTestopolis", "temp": 20.0, "description": "Clear sky", "temp_unit": "°C", "speed_unit": "m/s", "icon": "01d", "country": "CT", "feels_like": 19.0, "humidity": 50, "wind_speed": 5.0, "sunrise": "06:00:00 UTC", "sunset": "18:00:00 UTC"}
SAMPLE_PARSED_FORECAST_METRIC_FOR_CLI = [{"date": "2025-05-15 (Thu)", "temp_min": 15.0, "temp_max": 25.0, "description": "Sunny", "icon": "01d", "temp_unit": "°C"}]
SAMPLE_PARSED_WEATHER_IMPERIAL_FOR_CLI = {"city": "CliTestopolis", "temp": 68.0, "description": "Clear sky", "temp_unit": "°F", "speed_unit": "mph", "icon": "01d", "country": "CT", "feels_like": 66.0, "humidity": 50, "wind_speed": 11.2, "sunrise": "06:00:00 UTC", "sunset": "18:00:00 UTC"}
SAMPLE_PARSED_FORECAST_IMPERIAL_FOR_CLI = [{"date": "2025-05-15 (Thu)", "temp_min": 59.0, "temp_max": 77.0, "description": "Sunny", "icon": "01d", "temp_unit": "°F"}]

RAW_API_WEATHER_RESPONSE_FOR_CLI = {"name": "CliTestopolis", "weather": [{"icon": "01d"}], "main": {"temp": 20.0}, "sys": {"country": "CT"}, "wind": {"speed": 5.0}, "dt": 1747286400}
RAW_API_FORECAST_RESPONSE_FOR_CLI = {"list": [{"dt_txt": "2025-05-15 12:00:00", "main": {"temp": 20.0}, "weather": [{"description": "sunny", "icon": "01d"}]}], "city": {"name": "CliTestopolis"}}


def _assert_mock_print_any_call_contains_substring(mock_print_method: MagicMock, substring: str):
    found = False
    if not mock_print_method.called:
        assert found, f"Expected print call containing '{substring}' was not found. Mock was not called."

    for call_args_tuple in mock_print_method.call_args_list:
        args_tuple, _ = call_args_tuple
        if args_tuple:
            for arg_item in args_tuple:
                text_to_check = ""
                if isinstance(arg_item, Text):
                    text_to_check = arg_item.plain
                elif isinstance(arg_item, str):
                    text_to_check = arg_item
                else:
                    text_to_check = str(arg_item)
                
                if substring in text_to_check:
                    found = True
                    break
        if found:
            break
    assert found, f"Expected print call containing '{substring}' was not found. Calls made: {mock_print_method.call_args_list}"

def _assert_live_update_any_call_contains_substring(mock_live_update_method: MagicMock, substring: str):
    found = False
    if not mock_live_update_method.called:
        assert found, f"Expected Live().update call containing '{substring}' was not found. Mock was not called."
    
    for call_args_tuple in mock_live_update_method.call_args_list:
        args_tuple, _ = call_args_tuple
        if args_tuple and isinstance(args_tuple[0], (str, Text)): # Assuming update is called with one positional arg
            text_to_check = str(args_tuple[0].plain if isinstance(args_tuple[0], Text) else args_tuple[0])
            if substring in text_to_check:
                found = True
                break
        if found:
            break
    assert found, f"Expected Live().update call containing '{substring}' was not found. Calls: {mock_live_update_method.call_args_list}"


class TestCliArgumentParser:
    def _create_and_configure_parser(self):
        parser = argparse.ArgumentParser(description="CLI Weather App Test Parser")
        parser.add_argument("city", type=str, help="Name of the city to get weather for.")
        unit_group = parser.add_mutually_exclusive_group()
        unit_group.add_argument("--metric", action="store_const", dest="units", const="metric", help="Use Metric units.")
        unit_group.add_argument("--imperial", action="store_const", dest="units", const="imperial", help="Use Imperial units.")
        parser.set_defaults(units="metric")
        parser.add_argument("--no-cache", action="store_true", help="Force fetch fresh data from API, ignoring cache.")
        parser.add_argument("--clear-cache", metavar="CITY_NAME_OR_ALL", type=str, nargs='?', const="ALL", help="Clear cache.")
        return parser

    @pytest.mark.parametrize("input_args_list, expected_attributes_dict", [
        (["London"], {"city": "London", "units": "metric", "no_cache": False, "clear_cache": None}),
        (["Paris", "--metric"], {"city": "Paris", "units": "metric", "no_cache": False, "clear_cache": None}),
        (["Berlin", "--imperial"], {"city": "Berlin", "units": "imperial", "no_cache": False, "clear_cache": None}),
        (["Rome", "--no-cache"], {"city": "Rome", "units": "metric", "no_cache": True, "clear_cache": None}),
        (["Madrid", "--imperial", "--no-cache"], {"city": "Madrid", "units": "imperial", "no_cache": True, "clear_cache": None}),
        (["Vienna", "--clear-cache"], {"city": "Vienna", "units": "metric", "no_cache": False, "clear_cache": "ALL"}),
        (["Prague", "--clear-cache", "ALL"], {"city": "Prague", "units": "metric", "no_cache": False, "clear_cache": "ALL"}),
        (["Oslo", "--clear-cache", "OsloSpecific"], {"city": "Oslo", "units": "metric", "no_cache": False, "clear_cache": "OsloSpecific"}),
    ])
    def test_valid_argument_combinations_are_parsed_correctly(self, input_args_list, expected_attributes_dict):
        parser = self._create_and_configure_parser()
        args = parser.parse_args(input_args_list)
        for attr_name, expected_val in expected_attributes_dict.items():
            assert getattr(args, attr_name) == expected_val

    def test_default_units_is_metric_when_not_specified(self):
        parser = self._create_and_configure_parser()
        args = parser.parse_args(["Tokyo"])
        assert args.units == "metric"

    def test_clear_cache_flag_without_value_defaults_to_const_all(self):
        parser = self._create_and_configure_parser()
        args = parser.parse_args(["Amsterdam", "--clear-cache"])
        assert args.clear_cache == "ALL"

    def test_missing_city_argument_causes_parser_to_exit(self, capsys):
        parser = self._create_and_configure_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([])
        assert exc_info.value.code == 2
        stderr_output = capsys.readouterr().err
        assert "the following arguments are required: city" in stderr_output.lower()

    def test_mutually_exclusive_units_flags_cause_parser_to_exit(self, capsys):
        parser = self._create_and_configure_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["SomeCity", "--metric", "--imperial"])
        assert exc_info.value.code == 2
        stderr_output = capsys.readouterr().err
        assert "not allowed with argument" in stderr_output


@pytest.fixture
def mock_cli_dependencies(mocker):
    class MocksContainer:
        pass
    
    mocks = MocksContainer()

    mocks.db_get_cached_weather = mocker.patch('weather_cli.db.get_cached_weather', autospec=True)
    mocks.db_cache_weather = mocker.patch('weather_cli.db.cache_weather', autospec=True)
    mocks.db_clear_cache_for_city = mocker.patch('weather_cli.db.clear_cache_for_city', autospec=True)
    mocks.db_clear_all_cache = mocker.patch('weather_cli.db.clear_all_cache', autospec=True)
    
    mocks.api_get_weather_data = mocker.patch('weather_cli.weather_api.get_weather_data', autospec=True)
    mocks.api_get_forecast_data = mocker.patch('weather_cli.weather_api.get_forecast_data', autospec=True)
    mocks.api_parse_current_weather = mocker.patch('weather_cli.weather_api.parse_current_weather', autospec=True)
    mocks.api_parse_forecast = mocker.patch('weather_cli.weather_api.parse_forecast', autospec=True)
    
    mocks.display_current_weather = mocker.patch('weather_cli.cli.display_current_weather', autospec=True)
    mocks.display_forecast = mocker.patch('weather_cli.cli.display_forecast', autospec=True)
    
    PatchedConsoleClass = mocker.patch('weather_cli.cli.Console', autospec=True)
    mocks.console_instance = PatchedConsoleClass.return_value 
    mocks.console_print_method = mocks.console_instance.print

    mock_live_instance = MagicMock()
    mock_live_instance.__enter__.return_value = mock_live_instance 
    mock_live_instance.__exit__.return_value = None
    PatchedLiveClass = mocker.patch('weather_cli.cli.Live', autospec=True)
    PatchedLiveClass.return_value = mock_live_instance
    mocks.Live_instance_update_method = mock_live_instance.update
    
    mocker.patch.object(weather_api, 'API_KEY', 'cli_test_valid_api_key_fixture')
    
    return mocks


class TestRunCliExecutionLogic:

    def _call_run_cli_with_patched_argv(self, mock_deps, *cli_args):
        with patch('sys.argv', ['weather_cli_script_name_placeholder'] + list(cli_args)):
            cli.run_cli()

    def test_run_cli_exits_if_api_key_is_none(self, mock_cli_dependencies, capsys):
        with patch.object(cli.weather_api, 'API_KEY', None):
            self._call_run_cli_with_patched_argv(mock_cli_dependencies, "AnyValidCity")
        
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "API key (OPENWEATHERMAP_API_KEY) is not configured")
        mock_cli_dependencies.db_get_cached_weather.assert_not_called()
        mock_cli_dependencies.api_get_weather_data.assert_not_called()

    def test_run_cli_clears_all_cache_for_all_argument(self, mock_cli_dependencies, capsys):
        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "DummyCityArg", "--clear-cache", "ALL")
        mock_cli_dependencies.db_clear_all_cache.assert_called_once()
        mock_cli_dependencies.db_get_cached_weather.assert_not_called()

    def test_run_cli_clears_cache_for_specific_city(self, mock_cli_dependencies, capsys):
        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "DummyCityArg", "--clear-cache", "TargetCityToClear")
        mock_cli_dependencies.db_clear_cache_for_city.assert_called_once_with("TargetCityToClear")
        mock_cli_dependencies.db_get_cached_weather.assert_not_called()
        
    def test_run_cli_clear_cache_with_no_value_clears_all(self, mock_cli_dependencies, capsys):
        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "DummyCityArg", "--clear-cache")
        mock_cli_dependencies.db_clear_all_cache.assert_called_once()

    def test_run_cli_cache_hit_displays_data_and_not_calls_api(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = {
            "current": SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI, 
            "forecast": SAMPLE_PARSED_FORECAST_METRIC_FOR_CLI
        }
        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "CachedCity", "--metric")

        mock_cli_dependencies.db_get_cached_weather.assert_called_once_with("cachedcity_metric")
        mock_cli_dependencies.api_get_weather_data.assert_not_called()
        mock_cli_dependencies.api_get_forecast_data.assert_not_called()
        mock_cli_dependencies.display_current_weather.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI)
        mock_cli_dependencies.display_forecast.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_FORECAST_METRIC_FOR_CLI)
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "Cache hit for CachedCity (metric)!")

    def test_run_cli_cache_miss_fetches_parses_caches_and_displays_imperial(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = None
        mock_cli_dependencies.api_get_weather_data.return_value = RAW_API_WEATHER_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_get_forecast_data.return_value = RAW_API_FORECAST_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_current_weather.return_value = SAMPLE_PARSED_WEATHER_IMPERIAL_FOR_CLI
        mock_cli_dependencies.api_parse_forecast.return_value = SAMPLE_PARSED_FORECAST_IMPERIAL_FOR_CLI

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "FreshCity", "--imperial")

        mock_cli_dependencies.db_get_cached_weather.assert_called_once_with("freshcity_imperial")
        mock_cli_dependencies.api_get_weather_data.assert_called_once_with("FreshCity", units="imperial")
        mock_cli_dependencies.api_get_forecast_data.assert_called_once_with("FreshCity", units="imperial")
        mock_cli_dependencies.api_parse_current_weather.assert_called_once_with(RAW_API_WEATHER_RESPONSE_FOR_CLI, units="imperial")
        mock_cli_dependencies.api_parse_forecast.assert_called_once_with(RAW_API_FORECAST_RESPONSE_FOR_CLI, units="imperial")
        mock_cli_dependencies.db_cache_weather.assert_called_once_with("freshcity_imperial", SAMPLE_PARSED_WEATHER_IMPERIAL_FOR_CLI, SAMPLE_PARSED_FORECAST_IMPERIAL_FOR_CLI)
        mock_cli_dependencies.display_current_weather.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_WEATHER_IMPERIAL_FOR_CLI)
        mock_cli_dependencies.display_forecast.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_FORECAST_IMPERIAL_FOR_CLI)
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "Cache miss or expired for FreshCity (imperial)")

    def test_run_cli_no_cache_flag_skips_cache_read_and_fetches_data(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.api_get_weather_data.return_value = RAW_API_WEATHER_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_get_forecast_data.return_value = RAW_API_FORECAST_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_current_weather.return_value = SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI
        mock_cli_dependencies.api_parse_forecast.return_value = SAMPLE_PARSED_FORECAST_METRIC_FOR_CLI

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "NoCacheCity", "--no-cache")

        mock_cli_dependencies.db_get_cached_weather.assert_not_called()
        mock_cli_dependencies.api_get_weather_data.assert_called_once_with("NoCacheCity", units="metric")
        mock_cli_dependencies.db_cache_weather.assert_called_once()

    def test_run_cli_handles_get_weather_data_api_failure(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = None
        mock_cli_dependencies.api_get_weather_data.return_value = None

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "ApiFailCity")

        mock_cli_dependencies.api_get_weather_data.assert_called_once_with("ApiFailCity", units="metric")
        mock_cli_dependencies.api_get_forecast_data.assert_not_called()
        mock_cli_dependencies.db_cache_weather.assert_not_called()
        mock_cli_dependencies.display_current_weather.assert_not_called()
        mock_cli_dependencies.display_forecast.assert_not_called()
        _assert_live_update_any_call_contains_substring(mock_cli_dependencies.Live_instance_update_method, "Failed to retrieve current weather for ApiFailCity")


    def test_run_cli_handles_get_forecast_data_api_failure(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = None
        mock_cli_dependencies.api_get_weather_data.return_value = RAW_API_WEATHER_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_current_weather.return_value = SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI
        mock_cli_dependencies.api_get_forecast_data.return_value = None

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "ForecastFailCity")

        mock_cli_dependencies.api_get_forecast_data.assert_called_once_with("ForecastFailCity", units="metric")
        mock_cli_dependencies.db_cache_weather.assert_not_called()
        mock_cli_dependencies.display_current_weather.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI)
        mock_cli_dependencies.display_forecast.assert_not_called()
        _assert_live_update_any_call_contains_substring(mock_cli_dependencies.Live_instance_update_method, "Failed to retrieve forecast for ForecastFailCity")
        
    def test_run_cli_handles_parse_current_weather_failure(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = None
        mock_cli_dependencies.api_get_weather_data.return_value = RAW_API_WEATHER_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_current_weather.return_value = {} 
        mock_cli_dependencies.api_get_forecast_data.return_value = RAW_API_FORECAST_RESPONSE_FOR_CLI # This is fetched
        mock_cli_dependencies.api_parse_forecast.return_value = SAMPLE_PARSED_FORECAST_METRIC_FOR_CLI # And parsed

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "CurrentParseFail")

        mock_cli_dependencies.db_cache_weather.assert_not_called()
        mock_cli_dependencies.display_current_weather.assert_not_called()
        mock_cli_dependencies.display_forecast.assert_not_called() 
        # Corrected substring for Live().update()
        _assert_live_update_any_call_contains_substring(mock_cli_dependencies.Live_instance_update_method, "Failed to process or parse complete weather data for CurrentParseFail")
        # This print call happens outside the Live block, after Live exits.
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "Current weather data for CurrentParseFail is unavailable")
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "5-day forecast data for CurrentParseFail is unavailable or could not be processed")


    def test_run_cli_handles_parse_forecast_failure(self, mock_cli_dependencies, capsys):
        mock_cli_dependencies.db_get_cached_weather.return_value = None
        mock_cli_dependencies.api_get_weather_data.return_value = RAW_API_WEATHER_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_current_weather.return_value = SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI
        mock_cli_dependencies.api_get_forecast_data.return_value = RAW_API_FORECAST_RESPONSE_FOR_CLI
        mock_cli_dependencies.api_parse_forecast.return_value = [] 

        self._call_run_cli_with_patched_argv(mock_cli_dependencies, "ForecastParseFail")
        
        mock_cli_dependencies.db_cache_weather.assert_not_called()
        mock_cli_dependencies.display_current_weather.assert_called_once_with(mock_cli_dependencies.console_instance, SAMPLE_PARSED_WEATHER_METRIC_FOR_CLI)
        mock_cli_dependencies.display_forecast.assert_not_called()
        # Corrected substring for Live().update()
        _assert_live_update_any_call_contains_substring(mock_cli_dependencies.Live_instance_update_method, "Failed to process or parse complete weather data for ForecastParseFail")
        # This print call happens outside the Live block.
        _assert_mock_print_any_call_contains_substring(mock_cli_dependencies.console_print_method, "5-day forecast data for ForecastParseFail is unavailable")