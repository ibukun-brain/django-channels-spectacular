# Contributing

Contributions, bug reports, feature requests, and pull requests alike are welcome.

## Development setup

```bash
git clone https://github.com/ibukun-brain/django-channels-spectacular.git
cd django-channels-spectacular

# With pip
pip install -e ".[dev]"

# With uv (recommended)
uv sync --extra dev
```

## Running the tests

```bash
pytest -v
```

All tests must pass before a PR is merged. If you add new behaviour,
include tests that cover it.

## Coding style

- Follow existing code style; no trailing comments that restate what the code says.
- Keep functions and classes focused; prefer small named helpers over inline complexity.
- Public API changes must be reflected in docstrings and the README.

## Submitting a pull request

1. Fork the repository.
2. Make your changes and add tests.
3. Open a pull request with a clear title and description.
4. One feature or fix per PR makes review faster.

A quick cheat sheet to get you started
```bash
# fork the repo on github
git clone https://github.com/YOURGITHUBNAME/channels-spectacular
cd channels-spectacular
python -m venv venv
source venv/bin/activate
(venv) pip install -r requirements.txt
(venv) ./runtests.py  # runs tests (pytest) & linting (isort, flake8, mypy)
```

## Reporting bugs

Open a [GitHub issue](https://github.com/ibukun-brain/django-channels-spectacular/issues)
with the Python / Django / Channels versions, a minimal reproduction, and the full traceback.

## Requesting features

Open a GitHub issue describing the use-case you are trying to solve and any
API suggestions you have in mind.
