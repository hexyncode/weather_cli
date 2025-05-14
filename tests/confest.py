import pytest
import os

@pytest.fixture(autouse=True)
def set_dummy_env_api_key(monkeypatch):
    """
    Automatically set a dummy API key for the entire test session
    to prevent issues with module-level checks in weather_api.py during import.
    Actual API calls must still be mocked.
    """
    if not os.getenv("OPENWEATHERMAP_API_KEY"): # Avoid overriding if already set for other reasons
        monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test_dummy_api_key_for_pytest_session")