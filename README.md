# Python Weather CLI

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/hexyncode/weather_cli/blob/dev/pyproject.toml)
[![Build Status](https://img.shields.io/github/actions/workflow/status/hexyncode/weather_cli/ci.yml?branch=main)](https://github.com/hexyncode/weather_cli/actions/workflows/ci.yml)
[![Dependencies](https://img.shields.io/badge/dependencies-managed-brightgreen.svg)](requirements.txt)
[![Python Version](https://img.shields.io/badge/Python-3.13.3-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3133/)

A command-line interface (CLI) application to display the current weather and a 5-day forecast for a specified city using the OpenWeatherMap API. Features include selectable units (Metric/Imperial), colorized output, and local caching of results.

## Features

-   **Current Weather:** Displays temperature, "feels like" temperature, conditions, humidity, wind speed, sunrise, and sunset times.
-   **5-Day Forecast:** Shows a daily summary including minimum/maximum temperatures and prevailing weather conditions.
-   **Selectable Units:** Choose between Metric (`--metric`, default: Celsius, m/s) and Imperial (`--imperial`: Fahrenheit, mph) units for API data fetching and display.
-   **Clean Terminal Interface:** Utilizes `rich` for a visually appealing, readable, and colorized output.
-   **Error Handling:** Gracefully handles invalid city names, API key issues, and other API request failures.
-   **Unit-Specific Caching:** Caches recent searches in a local SQLite database (`weather_cache.db`) to reduce API calls and speed up subsequent lookups. Cache entries are specific to the city and the selected unit system (default cache duration: 30 minutes).

## Prerequisites

-   Python 3.7+
-   An active API key from [OpenWeatherMap](https://openweathermap.org/appid).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hexyncode/weather_cli.git
    cd weather_cli
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On macOS and Linux:
    source venv/bin/activate
    # On Windows:
    # venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key:**

    a.  In the root directory of the project (`weather_cli/`), copy the example environment file:

    ```bash
    cp .env.example .env
    ```
        
    b.  Open the newly created `.env` file with a text editor.

    c.  Replace `"YOUR_API_KEY_HERE"` with your actual OpenWeatherMap API key:
    ```env
    # .env
    OPENWEATHERMAP_API_KEY="YOUR_ACTUAL_API_KEY"
    ```

## Usage

Run the application from the root directory of the project (`weather_cli/`) using the following command structure:

```bash
python -m weather_cli.main <city_name> [options]
```

Alternatively, if you set up the project as an installable package (see "Making it Executable" below), you can run:

```bash
weather_app <city_name> [options]
```

### Options

| Option                       | Description                                                                                                                                 |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `city`                       | (Required) The name of the city for which to fetch weather data. Use quotes for multi-word city names (e.g., "New York").                  |
| `--metric`                   | Use Metric units (Celsius for temperature, m/s for wind speed). This is the **default** if no unit flag is specified.                     |
| `--imperial`                 | Use Imperial units (Fahrenheit for temperature, mph for wind speed).                                                                        |
| `--no-cache`                 | Force a fresh API call, ignoring any cached results for the specified city and unit combination.                                            |
| `--clear-cache [CITY_OR_ALL]`| Clear cache. If a city name is provided (e.g., `--clear-cache London`), clears cache for that city (both metric and imperial versions). If `ALL` or no argument is provided after the flag (e.g., `--clear-cache` or `--clear-cache ALL`), clears the entire cache. This action does not fetch new weather data. |

### Examples

-   **Get weather for London (default: metric units):**
    ```bash
    python -m weather_cli.main London
    ```
    or explicitly:
    ```bash
    python -m weather_cli.main London --metric
    ```

-   **Get weather for "New York" in Imperial units:**
    ```bash
    python -m weather_cli.main "New York" --imperial
    ```

-   **Force a fresh API call for Paris in Metric units, ignoring the cache:**
    ```bash
    python -m weather_cli.main Paris --metric --no-cache
    ```

-   **Clear the cache for a specific city (e.g., Berlin):**
    *(This clears cache for Berlin in both metric and imperial if they exist)*
    ```bash
    python -m weather_cli.main DummyCity --clear-cache Berlin
    ```
    *(Note: A placeholder city like "DummyCity" is required by the parser for the main city argument when using `--clear-cache` with a specific city name.)*

-   **Clear the entire weather cache:**
    ```bash
    python -m weather_cli.main DummyCity --clear-cache ALL
    # or simply:
    python -m weather_cli.main DummyCity --clear-cache
    ```

## Caching Details

The application caches successful API responses in a local SQLite database (`weather_cache.db`) located in the root project directory.
-   Cache entries are stored with a key combining the city name and the selected unit system (e.g., `london_metric`, `newyork_imperial`). This ensures that requests for the same city with different units are cached separately.
-   The default cache duration is 30 minutes.
-   Use the `--no-cache` flag to bypass the cache for a specific query.
-   Use the `--clear-cache` flag to manage cached data.

## Making it Executable (Optional)

To run the application more conveniently (e.g., as `weather_app London`), you can install it as a package in your environment.

1.  **Ensure you have a `pyproject.toml` file** in the root `weather_cli/` directory with the following content:

    ```toml
    [build-system]
    requires = ["setuptools>=42"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "weather_cli_app"
    version = "0.1.1" # Increment version as you make changes
    authors = [
      { name="Your Name", email="your.email@example.com" }, # Update with your details
    ]
    description = "A CLI weather application with selectable units and caching."
    readme = "README.md"
    requires-python = ">=3.7"
    classifiers = [
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License", # Or your chosen license
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "Topic :: Terminals",
    ]
    dependencies = [
        "requests",
        "rich",
        "python-dotenv",
    ]

    [project.scripts]
    weather_app = "weather_cli.main:main"
    ```

2.  **Install the package in editable mode** from the root `weather_cli/` directory:
    (Ensure your virtual environment is active)
    ```bash
    pip install -e .
    ```

3.  Now you should be able to run the app directly using the script name:
    ```bash
    weather_app London --imperial
    weather_app "San Francisco"
    ```

## Contributing

Contributions are welcome! If you have suggestions for improvements or find any bugs, please feel free to:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Create a new Pull Request.

### Running Tests Before Pushing Changes

To maintain code quality and ensure stability, all tests should pass before pushing any changes or opening a Pull Request. The project uses `pytest` for testing.

1.  **Ensure Test Dependencies are Installed:**
    If you haven't already, install all project dependencies, including those for testing, by running the following command from the project's root directory (ensure your virtual environment is active):
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run All Tests:**
    To execute the full test suite, navigate to the root directory of the project (`weather_cli/`) and run:
    ```bash
    pytest
    ```
    This command will discover and run all tests in the `tests/` directory. All tests must pass.

By running these tests locally, you can help ensure that your contributions integrate smoothly and do not introduce regressions.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
