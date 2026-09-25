#!/usr/bin/env python3

"""Render an HTML report for the GitHub commit history database.

The report summarizes each repository and embeds SVG circular charts for the
committers and languages stored in the SQLite database created by
store_github_commit_history.py.
"""

# pylint: disable=duplicate-code,line-too-long

import argparse
import html
import math
import sqlite3
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from project_config import ProjectConfig, load_config


@dataclass
class RepositorySummary:
    """
    A summary of a GitHub repository's commit history.
    """

    full_name: str
    last_status: str
    last_error: Optional[str]
    commit_total: int
    committer_total: int
    last_collected_at: str


@dataclass
class CommitterCount:
    """
    A simple data class representing a committer and their total commit count for a repository.
    """

    committer_name: str
    commit_count: int


@dataclass
class LanguageCount:
    """
    Aggregated language usage for a repository, measured in bytes and file count.
    """

    language_name: str
    byte_count: int
    file_count: int


@dataclass
class ChartSlice:
    """
    A single slice in a circular chart.
    """

    label: str
    value: int
    detail: str = ""
    color: Optional[str] = None


@dataclass(frozen=True)
class DonutRing:
    """Geometry of the donut chart, in SVG user units."""

    center_x: float
    center_y: float
    outer_radius: float
    inner_radius: float


@dataclass(frozen=True)
class CircleChartOptions:
    """Labels and coloring for one circular chart."""

    center_value: str
    center_label: str
    empty_message: str
    aria_label: str
    format_value: Callable[[int, float], str]
    hue_offset: float = 172.0


LANGUAGE_COLORS = {
    "Assembly": "#6E4C13",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "CMake": "#DA3434",
    "CSS": "#563d7c",
    "Dart": "#00B4AB",
    "Dockerfile": "#384d54",
    "Elixir": "#6e4a7e",
    "Go": "#00ADD8",
    "GraphQL": "#e10098",
    "HCL": "#844FBA",
    "HTML": "#e34c26",
    "Handlebars": "#f7931e",
    "Haskell": "#5e5086",
    "JSON": "#292929",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#DA5B0B",
    "Kotlin": "#A97BFF",
    "Less": "#1d365d",
    "Lua": "#000080",
    "Makefile": "#427819",
    "Markdown": "#083fa1",
    "PHP": "#4F5D95",
    "Perl": "#0298c3",
    "Prisma": "#0c344b",
    "Protocol Buffer": "#e4e4e4",
    "Python": "#3572A5",
    "R": "#198CE7",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "SCSS": "#c6538c",
    "SQL": "#e38c00",
    "Sass": "#a53b70",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "Solidity": "#AA6746",
    "Svelte": "#ff3e00",
    "Swift": "#F05138",
    "TOML": "#9c4221",
    "TypeScript": "#3178c6",
    "Vue": "#41b883",
    "XML": "#0060ac",
    "YAML": "#cb171e",
}


@dataclass
class GroupSummary:
    """
    A summary of a contributor group, aggregating commit counts and repositories
    across multiple members.
    """

    group_name: str
    commit_total: int
    repository_total: int
    members: List[str]


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the script.
    """
    parser = argparse.ArgumentParser(
        description="Create an HTML visualization for a GitHub commit history SQLite database."
    )
    parser.add_argument(
        "--config",
        help="Path to the project configuration file (default: config.toml next to this script).",
    )
    parser.add_argument(
        "--db",
        help="Path to the SQLite database file (default: the database path in the configuration).",
    )
    parser.add_argument(
        "--output",
        help="Path to the HTML report to generate (default: the report path in the configuration).",
    )
    return parser.parse_args()


def load_repositories(connection: sqlite3.Connection) -> List[RepositorySummary]:
    """
    Load all repositories from the database, returning a list of RepositorySummary objects.
    The results are ordered by repository full name for consistent display.
    If no repositories are found, an empty list is returned.
    """
    rows = connection.execute(
        """
        SELECT full_name, last_status, COALESCE(last_error, ''), commit_total,
               committer_total, last_collected_at
        FROM repositories
        ORDER BY full_name
        """
    ).fetchall()

    return [
        RepositorySummary(
            full_name=row[0],
            last_status=row[1],
            last_error=row[2] or None,
            commit_total=row[3],
            committer_total=row[4],
            last_collected_at=row[5],
        )
        for row in rows
    ]


def repository_name(full_name: str) -> str:
    """
    Return the repository name from a stored path or full name.
    """
    name = Path(full_name).name
    return name if name else full_name


def aggregate_committers(
    rows: List[tuple[str, int]],
    config: ProjectConfig,
) -> List[CommitterCount]:
    """
    Merge committers that share a display name or known alias, summing their commits.
    """
    member_index = config.member_index()
    grouped: dict[str, list] = {}
    for committer_name, commit_count in rows:
        group_name = member_index.get(committer_name.lower(), committer_name)
        key = group_name.lower()
        entry = grouped.setdefault(key, [group_name, 0])
        entry[1] += commit_count

    committers = [
        CommitterCount(committer_name=name, commit_count=count)
        for name, count in grouped.values()
    ]
    return sorted(committers, key=lambda item: (-item.commit_count, item.committer_name.lower()))


def load_committers(
    connection: sqlite3.Connection,
    repo_full_name: str,
    config: ProjectConfig,
) -> List[CommitterCount]:
    """
    Load all committers for a given repository from the database, returning a list of
    CommitterCount objects. Duplicate names and known aliases are merged by summing
    their commit counts. The results are ordered by commit count descending,
    then by committer name ascending for consistent display.
    If no committers are found for the repository, an empty list is returned.
    """
    rows = connection.execute(
        """
        SELECT committer_name, commit_count
        FROM committer_counts
        WHERE repo_full_name = ?
        ORDER BY commit_count DESC, committer_name ASC
        """,
        (repo_full_name,),
    ).fetchall()

    return aggregate_committers(rows, config)


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """
    Return True if the named table exists in the SQLite database.
    """
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def load_languages(
    connection: sqlite3.Connection,
    repo_full_name: str,
) -> List[LanguageCount]:
    """
    Load language usage for a repository, ordered by byte count descending.
    Returns an empty list when language data has not been collected yet.
    """
    if not table_exists(connection, "language_counts"):
        return []

    rows = connection.execute(
        """
        SELECT language_name, byte_count, file_count
        FROM language_counts
        WHERE repo_full_name = ?
        ORDER BY byte_count DESC, language_name ASC
        """,
        (repo_full_name,),
    ).fetchall()

    return [
        LanguageCount(language_name=row[0], byte_count=row[1], file_count=row[2])
        for row in rows
        if row[1] > 0
    ]


def load_contributor_rows(
    connection: sqlite3.Connection,
) -> List[tuple[str, str, str, int]]:
    """
    Load all contributor rows from the database, returning a list of tuples containing
    committer name, committer email, repository full name, and commit count. This data
    will be used to group contributors by the groups in the project configuration and
    to calculate totals for the contributor summary card. The results are ordered by committer
    name for consistent grouping.
    """
    return connection.execute(
        """
        SELECT committer_name, committer_email, repo_full_name, commit_count
        FROM committer_counts
        ORDER BY committer_name ASC
        """
    ).fetchall()


def group_contributors(
    rows: List[tuple[str, str, str, int]],
    config: ProjectConfig,
) -> List[GroupSummary]:
    """
    Group contributors by the groups in the project configuration,
    summing their commit counts and collecting the repositories they contributed to.
    Contributors not in any group are listed by their own name.
    """
    member_index = config.member_index()
    grouped: dict[str, dict[str, object]] = {}
    for committer_name, _committer_email, repo_full_name, commit_count in rows:
        group_name = member_index.get(committer_name.lower(), committer_name)
        key = group_name.lower()
        entry = grouped.setdefault(
            key,
            {
                "group_name": group_name,
                "commit_total": 0,
                "repos": set(),
                "members": set(),
            },
        )
        entry["commit_total"] += commit_count
        entry["repos"].add(repo_full_name)
        entry["members"].add(committer_name)

    summaries = [
        GroupSummary(
            group_name=entry["group_name"],
            commit_total=entry["commit_total"],
            repository_total=len(entry["repos"]),
            members=sorted(entry["members"]),
        )
        for entry in grouped.values()
    ]
    return sorted(summaries, key=lambda item: (-item.commit_total, item.group_name.lower()))


def load_schema(connection: sqlite3.Connection) -> None:
    """
    Load and validate the database schema. Raises RuntimeError if required tables are missing.
    """
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    required = {"repositories", "committer_counts"}
    missing = required - tables
    if missing:
        raise RuntimeError(f"Database is missing required tables: {', '.join(sorted(missing))}")


def status_badge(status: str) -> str:
    """
    Render an HTML badge for the repository status.
    """
    label = html.escape(status.title())
    return f'<span class="status status-{html.escape(status)}">{label}</span>'


def contributor_highlight_attribute(group_name: str, config: ProjectConfig) -> str:
    """
    Return a class attribute for contributor groups that should stand out in the summary.
    """
    if group_name.lower() in config.highlighted_groups():
        return ' class="highlighted"'
    return ""


def render_contributor_summary_card(
    connection: sqlite3.Connection,
    config: ProjectConfig,
) -> str:
    """
    Render an HTML card summarizing the contributors across all repositories,
    grouped by contributor groups.
    """
    rows = load_contributor_rows(connection)
    groups = group_contributors(rows, config)
    total_contributors = len(groups)

    if not groups:
        contributor_items = '<li class="empty">No contributors were found in the database.</li>'
    else:
        contributor_items = "".join(
            f"""
            <li{contributor_highlight_attribute(group.group_name, config)}>
                <strong>{html.escape(group.group_name)}</strong>
                <span class=\"members\">{html.escape(', '.join(group.members))}</span>
                <span>{group.commit_total} commits across {group.repository_total} repositories</span>
            </li>
            """
            for group in groups
        )

    return f"""
    <section class="summary-card">
        <div class="summary-header">
            <div>
                <p class="eyebrow">Contributors</p>
                <h2>Contributor Summary</h2>
            </div>
            <div class="summary-total">
                <span class="label">Unique contributors</span>
                <strong>{total_contributors}</strong>
            </div>
        </div>
        <ul class="contributor-list">
            {contributor_items}
        </ul>
    </section>
    """


def _polar(center_x: float, center_y: float, radius: float, angle_deg: float) -> tuple[float, float]:
    """
    Convert polar coordinates to SVG cartesian coordinates, with 0 degrees at the top.
    """
    angle_rad = math.radians(angle_deg - 90)
    return (
        center_x + radius * math.cos(angle_rad),
        center_y + radius * math.sin(angle_rad),
    )


def _full_ring_path(ring: DonutRing) -> str:
    """Build an SVG path for a donut that covers the whole circle."""
    return (
        f"M {ring.center_x:.3f} {ring.center_y - ring.outer_radius:.3f} "
        f"A {ring.outer_radius:.3f} {ring.outer_radius:.3f} 0 1 1 "
        f"{ring.center_x:.3f} {ring.center_y + ring.outer_radius:.3f} "
        f"A {ring.outer_radius:.3f} {ring.outer_radius:.3f} 0 1 1 "
        f"{ring.center_x:.3f} {ring.center_y - ring.outer_radius:.3f} "
        f"M {ring.center_x:.3f} {ring.center_y - ring.inner_radius:.3f} "
        f"A {ring.inner_radius:.3f} {ring.inner_radius:.3f} 0 1 0 "
        f"{ring.center_x:.3f} {ring.center_y + ring.inner_radius:.3f} "
        f"A {ring.inner_radius:.3f} {ring.inner_radius:.3f} 0 1 0 "
        f"{ring.center_x:.3f} {ring.center_y - ring.inner_radius:.3f} "
        "Z"
    )


def _donut_slice_path(ring: DonutRing, start_angle: float, end_angle: float) -> str:
    """
    Build an SVG path for a single donut slice.
    """
    sweep = end_angle - start_angle
    if sweep >= 359.999:
        return _full_ring_path(ring)

    large_arc = 1 if sweep > 180 else 0
    outer_start = _polar(ring.center_x, ring.center_y, ring.outer_radius, start_angle)
    outer_end = _polar(ring.center_x, ring.center_y, ring.outer_radius, end_angle)
    inner_end = _polar(ring.center_x, ring.center_y, ring.inner_radius, end_angle)
    inner_start = _polar(ring.center_x, ring.center_y, ring.inner_radius, start_angle)
    return (
        f"M {outer_start[0]:.3f} {outer_start[1]:.3f} "
        f"A {ring.outer_radius:.3f} {ring.outer_radius:.3f} 0 {large_arc} 1 "
        f"{outer_end[0]:.3f} {outer_end[1]:.3f} "
        f"L {inner_end[0]:.3f} {inner_end[1]:.3f} "
        f"A {ring.inner_radius:.3f} {ring.inner_radius:.3f} 0 {large_arc} 0 "
        f"{inner_start[0]:.3f} {inner_start[1]:.3f} "
        "Z"
    )


def _slice_color(index: int, hue_offset: float = 172.0) -> str:
    """
    Return a distinct HSL color for a chart slice.
    """
    hue = (hue_offset + index * 137.508) % 360
    return f"hsl({hue:.1f}, 48%, 42%)"


def format_bytes(byte_count: int) -> str:
    """
    Format a byte count into a compact human-readable size.
    """
    value = float(byte_count)
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} B"
    return f"{value:.1f} {units[unit_index]}"


@dataclass(frozen=True)
class SliceSpan:
    """Position of one slice within a circular chart."""

    index: int
    total: int
    start_angle: float
    end_angle: float


def _chart_piece(
    ring: DonutRing,
    item: ChartSlice,
    span: SliceSpan,
    options: CircleChartOptions,
) -> tuple[str, str]:
    """Return the SVG path and legend item for one chart slice."""
    color = item.color or _slice_color(span.index, options.hue_offset)
    percent = (item.value / span.total) * 100
    label = html.escape(item.label)
    detail = f" {html.escape(item.detail)}" if item.detail else ""
    value_label = html.escape(options.format_value(item.value, percent))
    path = (
        f'<path d="{_donut_slice_path(ring, span.start_angle, span.end_angle)}" '
        f'fill="{color}" stroke="#fffdf8" stroke-width="2">'
        f"<title>{label}: {options.format_value(item.value, percent)}{detail}</title>"
        "</path>"
    )
    legend = f"""
            <li>
                <span class="legend-swatch" style="background:{color}"></span>
                <span class="legend-name">{label}</span>
                <span class="legend-value">{value_label}</span>
            </li>
            """
    return path, legend


def _assemble_chart(
    ring: DonutRing,
    options: CircleChartOptions,
    paths: List[str],
    legend_items: List[str],
) -> str:
    """Wrap chart paths and legend items in the report markup."""
    return f"""
    <div class="chart-layout">
        <svg viewBox="0 0 360 360" class="pie-chart" role="img" aria-label="{html.escape(options.aria_label)}">
            {"".join(paths)}
            <text x="{ring.center_x}" y="{ring.center_y - 10}" class="pie-center-value">{html.escape(options.center_value)}</text>
            <text x="{ring.center_x}" y="{ring.center_y + 16}" class="pie-center-label">{html.escape(options.center_label)}</text>
        </svg>
        <ul class="chart-legend">
            {"".join(legend_items)}
        </ul>
    </div>
    """


def render_circle_chart(slices: List[ChartSlice], options: CircleChartOptions) -> str:
    """
    Render an SVG circular (donut) chart for the given slices.
    """
    total = sum(item.value for item in slices)
    if not slices or total == 0:
        return f'<p class="empty">{html.escape(options.empty_message)}</p>'

    ring = DonutRing(180.0, 180.0, 150.0, 82.0)
    paths = []
    legend_items = []
    current_angle = 0.0

    for index, item in enumerate(slices):
        sweep = (item.value / total) * 360
        end_angle = 360.0 if index == len(slices) - 1 else current_angle + sweep
        span = SliceSpan(index, total, current_angle, end_angle)
        path, legend = _chart_piece(ring, item, span, options)
        paths.append(path)
        legend_items.append(legend)
        current_angle = end_angle

    return _assemble_chart(ring, options, paths, legend_items)


def render_committer_chart(committers: List[CommitterCount]) -> str:
    """
    Render the circular chart of commit counts per committer.
    """
    slices = [
        ChartSlice(label=committer.committer_name, value=committer.commit_count)
        for committer in committers
        if committer.commit_count > 0
    ]
    total = sum(item.value for item in slices)
    return render_circle_chart(
        slices,
        CircleChartOptions(
            center_value=str(total),
            center_label="commits",
            empty_message="No committer counts stored for this repository.",
            aria_label="Commit counts per committer",
            format_value=lambda value, percent: f"{value} ({percent:.1f}%)",
            hue_offset=172.0,
        ),
    )


def render_language_chart(languages: List[LanguageCount]) -> str:
    """
    Render the circular chart of language usage for a repository.
    """
    slices = [
        ChartSlice(
            label=language.language_name,
            value=language.byte_count,
            detail=f"({language.file_count} files)",
            color=LANGUAGE_COLORS.get(language.language_name),
        )
        for language in languages
        if language.byte_count > 0
    ]
    total = sum(item.value for item in slices)
    return render_circle_chart(
        slices,
        CircleChartOptions(
            center_value=format_bytes(total) if total else "0 B",
            center_label="code",
            empty_message="No language data stored for this repository.",
            aria_label="Language usage by bytes of code",
            format_value=lambda value, percent: f"{format_bytes(value)} ({percent:.1f}%)",
            hue_offset=28.0,
        ),
    )


def render_repository_section(
    connection: sqlite3.Connection,
    repo: RepositorySummary,
    config: ProjectConfig,
) -> str:
    """
    Render an HTML section for a single repository, including its summary
    and circular charts for committers and languages.
    """
    committers = load_committers(connection, repo.full_name, config)
    languages = load_languages(connection, repo.full_name)
    error_html = ""
    if repo.last_error:
        error_html = f'<p class="error">{html.escape(repo.last_error)}</p>'

    return f"""
    <section class="repo-card">
        <header>
            <div>
                <h2>{html.escape(repository_name(repo.full_name))}</h2>
                <p class="meta">Collected at {html.escape(repo.last_collected_at)}</p>
            </div>
            {status_badge(repo.last_status)}
        </header>
        <div class="stats">
            <div><span class="label">Commits</span><strong>{repo.commit_total}</strong></div>
            <div><span class="label">Committers</span><strong>{len(committers)}</strong></div>
            <div><span class="label">Languages</span><strong>{len(languages)}</strong></div>
        </div>
        {error_html}
        <div class="repo-charts">
            <div class="chart-panel">
                <h3>Committers</h3>
                {render_committer_chart(committers)}
            </div>
            <div class="chart-panel">
                <h3>Languages</h3>
                {render_language_chart(languages)}
            </div>
        </div>
    </section>
    """


def render_html(
    repositories: List[RepositorySummary],
    connection: sqlite3.Connection,
    db_path: str,
    config: ProjectConfig,
) -> str:
    """
    Render the HTML report for the GitHub commit history.
    """
    sections = "\n".join(
        render_repository_section(connection, repo, config) for repo in repositories
    )
    if not sections:
        sections = (
            '<section class="repo-card"><p class="empty">'
            "No repositories were found in the database."
            "</p></section>"
        )

    total_commits = sum(repo.commit_total for repo in repositories)
    total_repositories = len(repositories)
    contributor_summary_card = render_contributor_summary_card(connection, config)
    report_title = html.escape(config.title)
    report_description = html.escape(config.description)
    stylesheet = Path(__file__).with_name("report.css").read_text(encoding="utf-8")

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{report_title}</title>
    <style>
{stylesheet}
    </style>
</head>
<body>
    <main class="page">
        <section class="hero">
            <h1>{report_title}</h1>
            <p>{report_description}</p>
        </section>

        {contributor_summary_card}

        <section class="overview" aria-label="summary">
            <div class="tile"><span class="label">Repositories</span><strong>{total_repositories}</strong></div>
            <div class="tile"><span class="label">Total commits</span><strong>{total_commits}</strong></div>
        </section>

        {sections}

        <p class="footer">Generated from {html.escape(db_path)}. Re-run the collector before regenerating the report to refresh the numbers.</p>
    </main>
</body>
</html>
"""


def main() -> int:
    """
    Main entry point for the script. Parses arguments, loads data from the database.
    """
    args = parse_args()
    try:
        config = load_config(Path(args.config) if args.config else None)
    except (FileNotFoundError, ValueError, OSError, tomllib.TOMLDecodeError) as error:
        print(error)
        return 1

    db_path = Path(args.db) if args.db else config.database
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    connection = None
    try:
        connection = sqlite3.connect(str(db_path))
        load_schema(connection)
        repositories = load_repositories(connection)
        html_report = render_html(repositories, connection, str(db_path), config)
    except (sqlite3.Error, RuntimeError) as error:
        print(f"Failed to build report: {error}")
        return 1
    finally:
        if connection is not None:
            connection.close()

    output_path = Path(args.output) if args.output else config.report
    output_path.write_text(html_report, encoding="utf-8")
    print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
