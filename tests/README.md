# Pirate Weather Integration Tests

This directory contains integration tests for the Pirate Weather Home Assistant custom component.

## Test Structure

- **conftest.py**: Common fixtures and test configuration
- **test_config_flow.py**: Tests for the configuration flow (setup and options)
- **test_init.py**: Tests for integration initialization, setup, and unload
 - **test_sensor.py**: Tests for sensors (state, attributes, and unit handling)
- **test_coordinator.py**: Tests for the weather data coordinator
- **fixtures/**: Sample API responses and test data

## Running Tests

### Quick Start

Run all tests:
```bash
./scripts/test
```

Run tests with verbose output:
```bash
./scripts/test -v
```

Run specific test file:
```bash
./scripts/test tests/test_config_flow.py
```

Run specific test function:
```bash
./scripts/test tests/test_config_flow.py::test_form
```

### Manual Setup

Install test dependencies:
```bash
pip install -r requirements_test.txt
```

Run tests:
```bash
pytest tests/
```

## Test Coverage

The current test suite covers:

- **Config Flow Tests** (`test_config_flow.py`):
  - User configuration flow
  - Invalid API key handling
  - Duplicate entry prevention
  - Options flow

- **Initialization Tests** (`test_init.py`):
  - Successful integration setup
  - Integration unload
  - Error handling during setup

- **Sensor Tests** (`test_sensor.py`):
  - Sensor entity state and attribute correctness
  - Unit and conversion handling for different unit systems
  - Availability handling when API data is missing or incomplete

- **Coordinator Tests** (`test_coordinator.py`):
  - Successful data updates
  - API error handling
  - Model exclusion parameters

## Adding New Tests

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use the fixtures defined in `conftest.py` for common setup
3. Mock external API calls using the `mock_aiohttp_session` fixture
4. Ensure tests are isolated and don't depend on each other
5. Add descriptive docstrings to test functions

## Continuous Integration

These tests are designed to run in CI/CD pipelines and should be run before merging any changes to ensure the integration continues to work correctly.
