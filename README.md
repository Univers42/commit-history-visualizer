# Transcendence Commit History Report

This project generates a report of the commit history for the ft_transcendence repositories.

## Prerequisites

- Python 3.10 or newer
- Git
- Make

## Usage

The Makefile automatically creates and uses a local project virtual environment when a target needs Python. Contributors do not need to activate it manually for the standard Make targets.

```bash
make help
make lint
make clone-repositories
make generate-report
make clean
```

### Optional manual setup

If you prefer to work in a virtual environment manually:

```bash
python3 -m venv venv
source ./venv/bin/activate
python -m pip install -r requirements.txt
```

The project already contains venv-aware shell entrypoints for repository cloning and report generation, so the Makefile delegates to those instead of duplicating the environment setup.

## Configuration

Read the [config.toml](config.toml) file to configure which repositories are cloned and how the report is generated.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.