# Transcendence Commit History Report

This project is a tool to generate a report of the commit history of the ft_transcendence project.

## Usage

### Create the virtual environment
```bash
python3 -m venv myvenv
```

### Activate the virtual environment
```bash
source ./myvenv/bin/activate
```

### Install the requirements
```bash
python3 -m pip install -r requirements.txt
```

### Clone the repository list from the [config.toml](config.toml)
```bash
make collect-git-commit-history
```

## Configuration

Read the `config.toml` file to configure the repositories to collect commit history from.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.