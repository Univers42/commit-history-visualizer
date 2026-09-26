#!/usr/bin/env python3

"""Clone or update the repositories listed in the project configuration."""

import argparse
import subprocess
import sys
from pathlib import Path

from project_config import ProjectConfig, load_config


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the clone tool."""
    parser = argparse.ArgumentParser(
        description="Clone or update the repositories listed in the project configuration."
    )
    parser.add_argument(
        "--config",
        help="Path to the project configuration file (default: config.toml next to this script).",
    )
    return parser.parse_args()


def sync_repository(config: ProjectConfig, name: str) -> None:
    """Clone a missing repository, or update an existing checkout onto the configured branch."""
    destination = config.clone_directory / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        subprocess.run(
            ["git", "-C", str(destination), "switch", config.clone_branch],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(destination), "pull", "--rebase", "origin", config.clone_branch],
            check=True,
        )
        return

    remote = f"{config.clone_remote}/{name}.git"
    subprocess.run(["git", "clone", remote, str(destination)], check=True)


def main() -> int:
    """
    Clone or update every repository in the configuration.
    Returns 1 when any repository fails.
    """
    args = parse_args()
    try:
        config = load_config(Path(args.config) if args.config else None)
    except (FileNotFoundError, ValueError, OSError) as error:
        print(error)
        return 1

    failures = 0
    for name in config.repositories:
        destination = config.clone_directory / name
        print(f"Syncing {name} ({destination})...")
        try:
            sync_repository(config, name)
        except (subprocess.CalledProcessError, OSError) as error:
            failures += 1
            print(f"Failed to sync {name}: {error}")

    print(f"Finished. Repositories: {len(config.repositories)}. Failed: {failures}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
