#!/usr/bin/env python3

"""Collect commit history from local Git repositories into SQLite.

The script accepts local repository paths either as positional arguments or
through a text file, stores commit history in SQLite, keeps per-committer
and per-language counts, and generates the HTML report after collection finishes.
"""

import argparse
import sqlite3
import subprocess
import sys
import webbrowser
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Optional, Tuple


DEFAULT_DB_PATH = "github_commit_history.sqlite3"
DEFAULT_REPORT_PATH = "github_commit_history_report.html"
GIT_LOG_FORMAT = "%H%x1f%cn%x1f%ce%x1f%cd%x1f%an%x1f%ae%x1f%ad%x1f%s"
GIT_LOG_SEPARATOR = "\x1f"

LANGUAGE_BY_EXTENSION = {
    ".asm": "Assembly",
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".h": "C",
    ".hh": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".go": "Go",
    ".graphql": "GraphQL",
    ".hbs": "Handlebars",
    ".hs": "Haskell",
    ".html": "HTML",
    ".htm": "HTML",
    ".ipynb": "Jupyter Notebook",
    ".java": "Java",
    ".js": "JavaScript",
    ".cjs": "JavaScript",
    ".mjs": "JavaScript",
    ".jsx": "JavaScript",
    ".json": "JSON",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".less": "Less",
    ".lua": "Lua",
    ".md": "Markdown",
    ".php": "PHP",
    ".pl": "Perl",
    ".pm": "Perl",
    ".prisma": "Prisma",
    ".proto": "Protocol Buffer",
    ".py": "Python",
    ".r": "R",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sass": "Sass",
    ".scala": "Scala",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sol": "Solidity",
    ".sql": "SQL",
    ".svelte": "Svelte",
    ".swift": "Swift",
    ".tf": "HCL",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
}

LANGUAGE_BY_FILENAME = {
    "cmakelists.txt": "CMake",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
}

SKIP_LANGUAGE_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "gemfile.lock",
    "cargo.lock",
    "poetry.lock",
}


# pylint: disable=duplicate-code


class GitRepositoryError(RuntimeError):
    """Raised when a local repository cannot be collected."""


@dataclass(frozen=True)
class RepositoryStatus:
    """Status values stored for a repository collection run."""

    full_name: str
    status: str
    error_message: Optional[str]
    commit_total: int
    committer_total: int


@dataclass
class CommitSummary:
    """Aggregated commit data for a repository collection."""

    commit_counts: DefaultDict[str, int]
    committer_names: dict[str, str]
    committer_emails: dict[str, str]
    commit_total: int


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the script.
    """
    parser = argparse.ArgumentParser(
        description="Store commit history from local Git repositories in SQLite."
    )
    parser.add_argument(
        "repos",
        nargs="*",
        help="Local repository paths. You can also provide them through --repos-file.",
    )
    parser.add_argument(
        "--repos-file",
        help=(
            "Path to a text file with one local repository path per line. Blank lines "
            "and lines starting with # are ignored."
        ),
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--report-output",
        default=DEFAULT_REPORT_PATH,
        help=f"Path to the HTML report to generate (default: {DEFAULT_REPORT_PATH}).",
    )
    return parser.parse_args()


def load_repositories_from_file(file_path: str) -> list[str]:
    """
    Load repository paths from a text file. Ignores blank lines and comments.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Repositories file not found: {path}")

    repositories = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        repositories.append(line)
    return repositories


def collect_input_repositories(args: argparse.Namespace) -> list[str]:
    """
    Collect the list of repository paths from command-line arguments or a file.
    Raises ValueError if no repositories are provided.
    """
    if args.repos:
        return list(args.repos)
    if args.repos_file:
        return load_repositories_from_file(args.repos_file)
    raise ValueError("You must provide repositories with --repos-file or as positional arguments.")


def ensure_schema(connection: sqlite3.Connection) -> None:
    """
    Ensure the database schema exists. Creates tables if they do not exist.
    """
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS repositories (
            full_name TEXT PRIMARY KEY,
            last_collected_at TEXT NOT NULL,
            last_status TEXT NOT NULL,
            last_error TEXT,
            commit_total INTEGER NOT NULL DEFAULT 0,
            committer_total INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS commits (
            repo_full_name TEXT NOT NULL,
            sha TEXT NOT NULL,
            committer_key TEXT NOT NULL,
            committer_name TEXT NOT NULL,
            author_name TEXT,
            author_email TEXT,
            committed_at TEXT,
            authored_at TEXT,
            message TEXT,
            url TEXT,
            PRIMARY KEY (repo_full_name, sha),
            FOREIGN KEY (repo_full_name) REFERENCES repositories(full_name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS committer_counts (
            repo_full_name TEXT NOT NULL,
            committer_key TEXT NOT NULL,
            committer_name TEXT NOT NULL,
            committer_email TEXT,
            commit_count INTEGER NOT NULL,
            PRIMARY KEY (repo_full_name, committer_key),
            FOREIGN KEY (repo_full_name) REFERENCES repositories(full_name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS language_counts (
            repo_full_name TEXT NOT NULL,
            language_name TEXT NOT NULL,
            byte_count INTEGER NOT NULL,
            file_count INTEGER NOT NULL,
            PRIMARY KEY (repo_full_name, language_name),
            FOREIGN KEY (repo_full_name) REFERENCES repositories(full_name) ON DELETE CASCADE
        );
        """
    )


def record_repository_status(
    connection: sqlite3.Connection,
    repo_status: RepositoryStatus,
) -> None:
    """
    Record the status of a repository in the database.
    """
    connection.execute(
        """
        INSERT INTO repositories (
            full_name, last_collected_at, last_status, last_error, commit_total, committer_total
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
            last_collected_at=excluded.last_collected_at,
            last_status=excluded.last_status,
            last_error=excluded.last_error,
            commit_total=excluded.commit_total,
            committer_total=excluded.committer_total
        """,
        (
            repo_status.full_name,
            datetime.now(timezone.utc).isoformat(),
            repo_status.status,
            repo_status.error_message,
            repo_status.commit_total,
            repo_status.committer_total,
        ),
    )


def insert_commits(
    connection: sqlite3.Connection,
    full_name: str,
    repository_path: Path,
) -> CommitSummary:
    """
    Insert commit rows for a repository and return aggregated committer data.
    """
    commit_counts: DefaultDict[str, int] = defaultdict(int)
    committer_names: dict[str, str] = {}
    committer_emails: dict[str, str] = {}
    commit_total = 0

    for fields in fetch_commits(repository_path):
        key = committer_key(fields[1], fields[2])
        commit_counts[key] += 1
        committer_names[key] = fields[1]
        committer_emails[key] = fields[2] or ""
        commit_total += 1

        connection.execute(
            """
            INSERT OR REPLACE INTO commits (
                repo_full_name, sha, committer_key, committer_name,
                author_name, author_email, committed_at, authored_at, message, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                fields[0],
                key,
                fields[1],
                fields[4] or None,
                fields[5] or None,
                fields[3],
                fields[6],
                fields[7],
                fields[0],
            ),
        )

    return CommitSummary(
        commit_counts=commit_counts,
        committer_names=committer_names,
        committer_emails=committer_emails,
        commit_total=commit_total,
    )


def insert_committer_counts(
    connection: sqlite3.Connection,
    full_name: str,
    summary: CommitSummary,
) -> None:
    """
    Insert aggregated committer counts for a repository.
    """
    for key, count in summary.commit_counts.items():
        connection.execute(
            """
            INSERT OR REPLACE INTO committer_counts (
                repo_full_name, committer_key, committer_name, committer_email, commit_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                full_name,
                key,
                summary.committer_names[key],
                summary.committer_emails[key],
                count,
            ),
        )


def classify_language(relative_path: str) -> Optional[str]:
    """
    Map a tracked file path to a language name, or None if it should be ignored.
    """
    path = Path(relative_path)
    filename = path.name.lower()
    if filename in SKIP_LANGUAGE_FILENAMES:
        return None
    if filename in LANGUAGE_BY_FILENAME:
        return LANGUAGE_BY_FILENAME[filename]
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower())


def collect_language_counts(repository_path: Path) -> list[tuple[str, int, int]]:
    """
    Count tracked source files by language, returning (language, bytes, files).
    """
    try:
        result = run_git_command(repository_path, ["ls-files", "-z"])
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        message = stderr or f"Failed to list files for {repository_path}"
        raise GitRepositoryError(message) from error

    totals: dict[str, list[int]] = {}
    for raw_path in result.stdout.split("\0"):
        relative_path = raw_path.strip()
        if not relative_path:
            continue
        language = classify_language(relative_path)
        if language is None:
            continue
        file_path = repository_path / relative_path
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        if size <= 0:
            continue
        entry = totals.setdefault(language, [0, 0])
        entry[0] += size
        entry[1] += 1

    return sorted(
        (
            (language, byte_count, file_count)
            for language, (byte_count, file_count) in totals.items()
        ),
        key=lambda item: (-item[1], item[0].lower()),
    )


def insert_language_counts(
    connection: sqlite3.Connection,
    full_name: str,
    language_counts: list[tuple[str, int, int]],
) -> None:
    """
    Insert aggregated language counts for a repository.
    """
    for language_name, byte_count, file_count in language_counts:
        connection.execute(
            """
            INSERT OR REPLACE INTO language_counts (
                repo_full_name, language_name, byte_count, file_count
            ) VALUES (?, ?, ?, ?)
            """,
            (full_name, language_name, byte_count, file_count),
        )


def normalize_repository_path(reference: str) -> Path:
    """
    Validate and normalize the repository path. Raises GitRepositoryError if the path is invalid.
    """
    path = Path(reference).expanduser()
    if not path.exists():
        raise GitRepositoryError(f"Repository path does not exist: {reference}")
    if not path.is_dir():
        raise GitRepositoryError(f"Repository path is not a directory: {reference}")
    return path.resolve()


def run_git_command(repository_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """
    Run a git command in the specified repository and return the completed process.
    Raises CalledProcessError on failure.
    """
    return subprocess.run(
        ["git", "-C", str(repository_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def repository_display_name(repository_path: Path) -> str:
    """
    Generate a user-friendly display name for the repository based on its remote URL or path.
    """
    try:
        remote = run_git_command(repository_path, ["remote", "get-url", "origin"]).stdout.strip()
    except subprocess.CalledProcessError:
        return repository_path.name

    if remote.endswith(".git"):
        remote = remote[:-4]

    if remote.startswith("git@github.com:"):
        remote = remote.removeprefix("git@github.com:")
    elif remote.startswith(("https://github.com/", "http://github.com/")):
        remote = remote.split("github.com/", 1)[-1]

    parts = [part for part in remote.strip("/").split("/") if part]
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return repository_path.name


def parse_git_log_line(line: str) -> Tuple[str, str, str, str, str, str, str, str]:
    """
    Parse a single line from the git log output into its component parts.
    """
    fields = line.split(GIT_LOG_SEPARATOR, 7)
    if len(fields) != 8:
        raise GitRepositoryError("Unexpected git log output format")
    return (
        fields[0],
        fields[1],
        fields[2],
        fields[3],
        fields[4],
        fields[5],
        fields[6],
        fields[7],
    )


def fetch_commits(repository_path: Path):
    """
    Fetch commit history from the repository using git log and yield parsed commit data.
    """
    try:
        result = run_git_command(
            repository_path,
            ["log", "--all", f"--pretty=format:{GIT_LOG_FORMAT}", "--date=iso-strict"],
        )
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        message = stderr or f"Failed to read git history for {repository_path}"
        raise GitRepositoryError(message) from error

    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        yield parse_git_log_line(raw_line)


def committer_key(name: str, email: str) -> str:
    """
    Generate a unique key for a committer based on their email or name.
    """
    if email:
        return f"email:{email.lower()}"
    return f"name:{name.lower()}"


def store_repository(connection: sqlite3.Connection, repository_reference: str) -> bool:
    """
    Collect commit history for a single repository and store it in the database.
    Returns True on success, False on failure.
    """
    try:
        repository_path = normalize_repository_path(repository_reference)
        full_name = str(repository_path)
        display_name = repository_display_name(repository_path)

        print(f"Collecting {display_name} ({repository_path})...")

        with connection:
            record_repository_status(
                connection,
                RepositoryStatus(full_name, "collecting", None, 0, 0),
            )
            connection.execute("DELETE FROM commits WHERE repo_full_name = ?", (full_name,))
            connection.execute(
                "DELETE FROM committer_counts WHERE repo_full_name = ?",
                (full_name,),
            )
            connection.execute(
                "DELETE FROM language_counts WHERE repo_full_name = ?",
                (full_name,),
            )

            summary = insert_commits(connection, full_name, repository_path)
            insert_committer_counts(connection, full_name, summary)
            insert_language_counts(connection, full_name, collect_language_counts(repository_path))
            record_repository_status(
                connection,
                RepositoryStatus(
                    full_name,
                    "success",
                    None,
                    summary.commit_total,
                    len(summary.commit_counts),
                ),
            )

        print(f"Stored {summary.commit_total} commits for {display_name}.")
        return True
    except (GitRepositoryError, sqlite3.Error, OSError, ValueError) as error:
        full_name = str(Path(repository_reference).expanduser())
        print(f"Failed to collect {full_name}: {error}")
        try:
            with connection:
                record_repository_status(
                    connection,
                    RepositoryStatus(full_name, "error", str(error), 0, 0),
                )
        except sqlite3.Error as status_error:
            print(f"Failed to record status for {full_name}: {status_error}")
        return False


def generate_report(db_path: str, report_output: str) -> None:
    """
    Generate the HTML report by running the visualization script and open it in a browser.
    """
    report_script = Path(__file__).with_name("github_commit_history_visualizer.py")
    subprocess.run(
        [
            sys.executable,
            str(report_script),
            "--db",
            db_path,
            "--output",
            report_output,
        ],
        check=True,
    )
    webbrowser.open(Path(report_output).resolve().as_uri())


def main() -> int:
    """
    Main entry point for the script. Parses arguments, collects repositories,
    stores commit history, and generates the report. Returns 0 on success, or 1 on failure.
    """
    args = parse_args()
    try:
        repositories = collect_input_repositories(args)
    except (FileNotFoundError, ValueError) as error:
        print(error)
        return 1

    if not repositories:
        print("You must provide at least one repository.")
        return 1

    try:
        connection = sqlite3.connect(args.db)
    except sqlite3.Error as error:
        print(f"Unable to open database '{args.db}': {error}")
        return 1

    success_count = 0
    failure_count = 0

    try:
        ensure_schema(connection)
        for repository in repositories:
            if store_repository(connection, repository):
                success_count += 1
            else:
                failure_count += 1
    finally:
        connection.close()

    try:
        generate_report(args.db, args.report_output)
    except subprocess.CalledProcessError as error:
        print(f"Failed to generate the HTML report: {error}")
    except (OSError, webbrowser.Error) as error:
        print(f"Failed to open the HTML report in a browser: {error}")

    print(
        f"Finished. Successful repositories: {success_count}. Failed repositories: {failure_count}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
