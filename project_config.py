#!/usr/bin/env python3

"""Load the project configuration shared by the clone, collect, and report tools."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_DESCRIPTION = (
    "This report visualizes the repository history stored in the SQLite database, "
    "with per-repository totals and circular charts for committers and languages."
)


@dataclass(frozen=True)
class ContributorGroup:
    """A person represented by one or more committer names."""

    name: str
    members: tuple[str, ...]
    highlight: bool


@dataclass(frozen=True)
class ProjectConfig:
    """Settings that adapt the tools to one set of repositories and users."""

    source: Path
    name: str
    title: str
    description: str
    database: Path
    report: Path
    clone_remote: str
    clone_directory: Path
    clone_branch: str
    repositories: tuple[str, ...]
    groups: tuple[ContributorGroup, ...]

    def repository_paths(self) -> list[Path]:
        """Return the local checkout path for every configured repository."""
        return [self.clone_directory / name for name in self.repositories]

    def member_index(self) -> dict[str, str]:
        """Map a committer name, in lowercase, to its configured group name."""
        index: dict[str, str] = {}
        for group in self.groups:
            for member in (group.name, *group.members):
                index[member.lower()] = group.name
        return index

    def highlighted_groups(self) -> set[str]:
        """Return the lowercase names of groups marked for the summary highlight."""
        return {group.name.lower() for group in self.groups if group.highlight}


def default_config_path() -> Path:
    """Return the configuration file that sits next to this module."""
    return Path(__file__).with_name("config.toml")


def load_config(path: Path | None = None) -> ProjectConfig:
    """
    Load a configuration file. Relative paths inside it are resolved from the
    file's directory. Raises FileNotFoundError or ValueError when the file is
    missing or invalid.
    """
    config_path = (path or default_config_path()).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _parse_config(config_path.resolve(), raw)


def _parse_config(source: Path, raw: dict) -> ProjectConfig:
    base = source.parent
    name = _require_string(raw, "name", source)
    title = _optional_string(raw, "title", source) or f"{name} Commit History"
    description = _optional_string(raw, "description", source) or DEFAULT_DESCRIPTION
    database = _as_path(base, _require_string(raw, "database", source))
    report = _as_path(base, _require_string(raw, "report", source))

    clone = raw.get("clone", {})
    if not isinstance(clone, dict):
        raise ValueError(f"{source}: 'clone' must be a table")
    clone_remote = _require_string(clone, "remote", source, "clone.remote").rstrip("/")
    clone_directory = _as_path(base, _require_string(clone, "directory", source, "clone.directory"))
    clone_branch = _optional_string(clone, "branch", source, "clone.branch") or "main"

    repositories = _parse_repositories(raw.get("repositories"), source)
    groups = _parse_groups(raw.get("groups", []), source)
    _reject_duplicate_members(groups, source)

    return ProjectConfig(
        source=source,
        name=name,
        title=title,
        description=description,
        database=database,
        report=report,
        clone_remote=clone_remote,
        clone_directory=clone_directory,
        clone_branch=clone_branch,
        repositories=repositories,
        groups=groups,
    )


def _parse_repositories(value: object, source: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{source}: 'repositories' must be a non-empty list of names")

    names: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{source}: every repository entry must be a non-empty name")
        name = item.strip()
        if name in seen:
            raise ValueError(f"{source}: duplicate repository '{name}'")
        seen.add(name)
        names.append(name)
    return tuple(names)


def _parse_groups(value: object, source: Path) -> tuple[ContributorGroup, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source}: 'groups' must be an array of tables")

    groups: list[ContributorGroup] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{source}: every group must be a table with 'name' and 'members'")
        name = _require_string(item, "name", source, "groups.name")
        if name.lower() in seen:
            raise ValueError(f"{source}: duplicate group '{name}'")
        seen.add(name.lower())

        members_value = item.get("members", [])
        if not isinstance(members_value, list) or not all(
            isinstance(member, str) and member.strip() for member in members_value
        ):
            raise ValueError(f"{source}: group '{name}' members must be a list of names")
        highlight = item.get("highlight", False)
        if not isinstance(highlight, bool):
            raise ValueError(f"{source}: group '{name}' highlight must be true or false")

        members = tuple(dict.fromkeys(member.strip() for member in members_value))
        groups.append(ContributorGroup(name=name, members=members, highlight=highlight))
    return tuple(groups)


def _reject_duplicate_members(groups: tuple[ContributorGroup, ...], source: Path) -> None:
    owners: dict[str, str] = {}
    for group in groups:
        for member in (group.name, *group.members):
            key = member.lower()
            owner = owners.get(key)
            if owner and owner.lower() != group.name.lower():
                raise ValueError(
                    f"{source}: '{member}' belongs to both '{owner}' and '{group.name}'"
                )
            owners[key] = group.name


def _as_path(base: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _require_string(raw: dict, key: str, source: Path, label: str | None = None) -> str:
    value = raw.get(key)
    field = label or key
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}: '{field}' must be a non-empty string")
    return value.strip()


def _optional_string(
    raw: dict,
    key: str,
    source: Path,
    label: str | None = None,
) -> str | None:
    if key not in raw or raw[key] is None:
        return None
    return _require_string(raw, key, source, label)
