#!/usr/bin/env python3
"""Interactive JSON diff tool that periodically fetches and compares JSON from URLs."""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from deepdiff import DeepDiff
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()


class JSONDiffWatcher:
    """Watch and diff JSON from a URL with filtering and colored output."""

    def __init__(
        self,
        url: str,
        interval: float = 2.0,
        filter_path: Optional[str] = None,
        filter_key: Optional[str] = None,
        filter_value: Optional[str] = None,
        show_only_diffs: bool = False,
        headers: Optional[dict] = None,
    ):
        """Initialize the JSON diff watcher.

        Args:
            url: URL to fetch JSON from
            interval: Polling interval in seconds
            filter_path: JSONPath-like path to filter (e.g., 'items[*]')
            filter_key: Key to filter objects by (e.g., 'id')
            filter_value: Value to match for filter_key
            show_only_diffs: If True, show only the differences
            headers: Optional HTTP headers to send with requests
        """
        self.url = url
        self.interval = interval
        self.filter_path = filter_path
        self.filter_key = filter_key
        self.filter_value = filter_value
        self.show_only_diffs = show_only_diffs
        self.headers = headers or {}
        self.previous_data: Optional[Any] = None
        self.previous_filtered: Optional[Any] = None
        self.storage_file = (
            Path.home()
            / ".jsondiff_cache"
            / f"{urlparse(url).netloc.replace('.', '_')}.json"
        )

    def fetch_json(self) -> Optional[Any]:
        """Fetch JSON from the URL.

        Returns:
            Parsed JSON data or None if fetch fails
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching JSON:[/red] {e}")
            return None
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON:[/red] {e}")
            return None

    def filter_json(self, data: Any) -> Any:
        """Filter JSON data based on provided filters.

        Args:
            data: JSON data to filter

        Returns:
            Filtered JSON data
        """
        if not any([self.filter_path, self.filter_key]):
            return data

        result = data

        # Apply JSONPath-like filtering
        if self.filter_path:
            result = self._apply_path_filter(result, self.filter_path)

        # Apply key-value filtering
        if self.filter_key and isinstance(result, list):
            filtered = []
            for item in result:
                if isinstance(item, dict) and self.filter_key in item:
                    if (
                        self.filter_value is None
                        or str(item[self.filter_key]) == self.filter_value
                    ):
                        filtered.append(item)
            result = filtered
        elif self.filter_key and isinstance(result, dict):
            if self.filter_key in result:
                if (
                    self.filter_value is None
                    or str(result[self.filter_key]) == self.filter_value
                ):
                    result = {self.filter_key: result[self.filter_key]}
                else:
                    result = {}
            else:
                # Try to find the key in nested structures
                result = self._find_and_filter_key(
                    result, self.filter_key, self.filter_value
                )

        return result

    def _apply_path_filter(self, data: Any, path: str) -> Any:
        """Apply a simple JSONPath-like filter.

        Args:
            data: JSON data
            path: Path like 'items[*]' or 'data.items[0]'

        Returns:
            Filtered data
        """
        parts = path.split(".")
        result = data

        for part in parts:
            if "[" in part and "]" in part:
                key = part[: part.index("[")]
                index_part = part[part.index("[") + 1 : part.index("]")]
                if key:
                    result = result.get(key, {})
                if index_part == "*":
                    # Return all items in list
                    if isinstance(result, list):
                        continue
                    else:
                        return {}
                else:
                    try:
                        idx = int(index_part)
                        if isinstance(result, list) and 0 <= idx < len(result):
                            result = result[idx]
                        else:
                            return {}
                    except ValueError:
                        return {}
            else:
                if isinstance(result, dict):
                    result = result.get(part, {})
                else:
                    return {}

        return result

    def _find_and_filter_key(self, data: Any, key: str, value: Optional[str]) -> Any:
        """Recursively find and filter by key.

        Args:
            data: JSON data
            key: Key to find
            value: Optional value to match

        Returns:
            Filtered data
        """
        if isinstance(data, dict):
            if key in data:
                if value is None or str(data[key]) == value:
                    return {key: data[key]}
            result = {}
            for k, v in data.items():
                filtered = self._find_and_filter_key(v, key, value)
                if filtered:
                    result[k] = filtered
            return result if result else None
        elif isinstance(data, list):
            result = []
            for item in data:
                filtered = self._find_and_filter_key(item, key, value)
                if filtered:
                    result.append(filtered)
            return result if result else None
        return None

    def save_previous(self, data: Any):
        """Save previous data to file for persistence.

        Args:
            data: Data to save
        """
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not save previous data:[/yellow] {e}"
            )

    def load_previous(self) -> Optional[Any]:
        """Load previous data from file.

        Returns:
            Previous data or None
        """
        try:
            if self.storage_file.exists():
                with open(self.storage_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not load previous data:[/yellow] {e}"
            )
        return None

    def format_diff(self, diff: DeepDiff) -> str:
        """Format DeepDiff output for display.

        Args:
            diff: DeepDiff object

        Returns:
            Formatted diff string
        """
        if not diff:
            return ""

        output_lines = []
        output_lines.append("[bold cyan]Changes detected:[/bold cyan]\n")

        # Dictionary items added
        if "dictionary_item_added" in diff:
            output_lines.append("[green]Added items:[/green]")
            for item in diff["dictionary_item_added"]:
                output_lines.append(f"  [green]+[/green] {item}")
            output_lines.append("")

        # Dictionary items removed
        if "dictionary_item_removed" in diff:
            output_lines.append("[red]Removed items:[/red]")
            for item in diff["dictionary_item_removed"]:
                output_lines.append(f"  [red]-[/red] {item}")
            output_lines.append("")

        # Values changed
        if "values_changed" in diff:
            output_lines.append("[yellow]Changed values:[/yellow]")
            for path, change in diff["values_changed"].items():
                old_val = change.get("old_value", "N/A")
                new_val = change.get("new_value", "N/A")
                output_lines.append(f"  [yellow]~[/yellow] {path}")
                output_lines.append(f"    [red]-[/red] {old_val}")
                output_lines.append(f"    [green]+[/green] {new_val}")
            output_lines.append("")

        # Items added to list
        if "iterable_item_added" in diff:
            output_lines.append("[green]Items added to list:[/green]")
            for path, value in diff["iterable_item_added"].items():
                output_lines.append(f"  [green]+[/green] {path}: {value}")
            output_lines.append("")

        # Items removed from list
        if "iterable_item_removed" in diff:
            output_lines.append("[red]Items removed from list:[/red]")
            for path, value in diff["iterable_item_removed"].items():
                output_lines.append(f"  [red]-[/red] {path}: {value}")
            output_lines.append("")

        return "\n".join(output_lines)

    def display_diff(self, current: Any, previous: Any):
        """Display the difference between current and previous data.

        Args:
            current: Current JSON data
            previous: Previous JSON data
        """
        # Filter both if needed
        current_filtered = self.filter_json(current)
        previous_filtered = self.filter_json(previous) if previous else None

        # Calculate diff
        if previous_filtered is None:
            console.print(
                Panel(
                    Group(
                        Text("Initial data loaded", style="green"),
                        Syntax(
                            json.dumps(current_filtered, indent=2),
                            "json",
                            theme="monokai",
                        ),
                    ),
                    title="[bold]JSON Watch[/bold]",
                    border_style="green",
                )
            )
            return

        diff = DeepDiff(
            previous_filtered, current_filtered, ignore_order=False, verbose_level=2
        )

        if not diff:
            console.print("[dim]No changes detected.[/dim]")
            return

        # Show only diffs or full comparison
        if self.show_only_diffs:
            diff_text = self.format_diff(diff)
            console.print(
                Panel(
                    diff_text,
                    title="[bold]JSON Differences[/bold]",
                    border_style="yellow",
                )
            )
        else:
            # Show side-by-side comparison
            table = Table(
                box=box.ROUNDED, show_header=True, header_style="bold magenta"
            )
            table.add_column("Previous", style="red", width=40)
            table.add_column("Current", style="green", width=40)

            prev_str = json.dumps(previous_filtered, indent=2)
            curr_str = json.dumps(current_filtered, indent=2)

            # Split into lines for comparison
            prev_lines = prev_str.split("\n")
            curr_lines = curr_str.split("\n")
            max_lines = max(len(prev_lines), len(curr_lines))

            for i in range(max_lines):
                prev_line = prev_lines[i] if i < len(prev_lines) else ""
                curr_line = curr_lines[i] if i < len(curr_lines) else ""
                table.add_row(prev_line, curr_line)

            console.print(
                Panel(table, title="[bold]JSON Comparison[/bold]", border_style="cyan")
            )

            # Also show the formatted diff
            diff_text = self.format_diff(diff)
            if diff_text:
                console.print(
                    Panel(
                        diff_text,
                        title="[bold]Changes Summary[/bold]",
                        border_style="yellow",
                    )
                )

    def run(self):
        """Run the watcher loop."""
        console.print(f"[bold cyan]Watching JSON from:[/bold cyan] {self.url}")
        console.print(f"[dim]Interval: {self.interval} seconds[/dim]")
        if self.filter_path or self.filter_key:
            console.print(
                f"[dim]Filter: path={self.filter_path}, key={self.filter_key}, value={self.filter_value}[/dim]"
            )
        console.print("")

        # Load previous data if exists
        self.previous_data = self.load_previous()

        try:
            while True:
                current_data = self.fetch_json()
                if current_data is None:
                    time.sleep(self.interval)
                    continue

                if self.previous_data is not None:
                    self.display_diff(current_data, self.previous_data)
                else:
                    # First run - just display initial data
                    self.display_diff(current_data, None)

                self.previous_data = current_data
                self.save_previous(current_data)

                time.sleep(self.interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped by user[/yellow]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Watch and diff JSON from URLs with filtering and colored output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s https://api.example.com/data

  # With filtering by path
  %(prog)s https://api.example.com/data --filter-path "items[*]"

  # Filter objects by key-value
  %(prog)s https://api.example.com/data --filter-key "status" --filter-value "active"

  # Show only differences
  %(prog)s https://api.example.com/data --show-only-diffs

  # Custom interval and headers
  %(prog)s https://api.example.com/data -i 5 --header "Authorization: Bearer token"
        """,
    )

    _ = parser.add_argument("url", help="URL to fetch JSON from")
    _ = parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2.0)",
    )
    _ = parser.add_argument(
        "--filter-path",
        type=str,
        default=None,
        help='JSONPath-like path to filter (e.g., "items[*]" or "data.items[0]")',
    )
    _ = parser.add_argument(
        "--filter-key",
        type=str,
        default=None,
        help='Key to filter objects by (e.g., "id", "status")',
    )
    _ = parser.add_argument(
        "--filter-value",
        type=str,
        default=None,
        help="Value to match for filter-key (optional)",
    )
    _ = parser.add_argument(
        "--show-only-diffs",
        action="store_true",
        help="Show only the differences, not full comparison",
    )
    _ = parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        help='HTTP header to send (can be used multiple times, format: "Key: Value")',
    )

    args = parser.parse_args()

    # Parse headers
    headers = {}
    if args.headers:
        for header in args.headers:
            if ":" in header:
                key, value = header.split(":", 1)
                headers[key.strip()] = value.strip()

    watcher = JSONDiffWatcher(
        url=args.url,
        interval=args.interval,
        filter_path=args.filter_path,
        filter_key=args.filter_key,
        filter_value=args.filter_value,
        show_only_diffs=args.show_only_diffs,
        headers=headers,
    )

    watcher.run()


if __name__ == "__main__":
    main()
