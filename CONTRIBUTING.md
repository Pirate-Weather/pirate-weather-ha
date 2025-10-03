# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the Apache-2.0 License

In short, when you submit code changes, your submissions are understood to be under the same [Apache-2.0](https://github.com/Pirate-Weather/pirate-weather-ha?tab=Apache-2.0-1-ov-file#readme) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](https://github.com/Pirate-Weather/pirate-weather-ha/issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](https://github.com/Pirate-Weather/pirate-weather-ha/issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [Ruff formater](https://docs.astral.sh/ruff/formatter/) to make sure the code follows the style.

## Test your code modification

This custom component is based on [integration_blueprint template](https://github.com/ludeeus/integration_blueprint).

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml)
file.

### Running Tests

The project includes a comprehensive test suite to ensure the integration works correctly. Before submitting a pull request, please:

1. Install test dependencies:
   ```bash
   pip install -r requirements_test.txt
   ```

2. Run the tests:
   ```bash
   ./scripts/test
   ```

   Or manually:
   ```bash
   pytest tests/
   ```

3. Ensure all tests pass and add new tests for any new functionality.

For more information about the test suite, see [tests/README.md](tests/README.md).

## License

By contributing, you agree that your contributions will be licensed under its Apache-2.0 License.
