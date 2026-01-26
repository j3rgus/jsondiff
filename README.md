# jsondiff

An interactive JSON diff tool that periodically fetches JSON from URLs and displays differences between consecutive fetches with beautiful, colorized output.

## Features

- 🔄 **Periodic Monitoring**: Automatically fetches JSON from URLs at configurable intervals
- 🔍 **Deep Comparison**: Uses DeepDiff to detect all types of changes (added, removed, modified items)
- 🎨 **Rich Output**: Beautiful terminal output with syntax highlighting and colorized diffs
- 🔎 **Filtering**: Filter JSON data by path, key, or key-value pairs
- 💾 **Persistence**: Saves previous state to disk for comparison across restarts
- 📊 **Multiple Views**: Show only differences or full side-by-side comparison
- 🔐 **Custom Headers**: Support for authentication and custom HTTP headers

## Installation

```bash
pip install -r requirements.txt
```

Or install the package:

```bash
pip install .
```

## Usage

### Basic Usage

Watch a JSON endpoint and display changes:

```bash
jsondiff https://api.example.com/data
```

### Filter by JSONPath-like Path

Filter to specific parts of the JSON structure:

```bash
jsondiff https://api.example.com/data --filter-path "items[*]"
```

```bash
jsondiff https://api.example.com/data --filter-path "data.items[0]"
```

### Filter by Key-Value

Filter objects that match a specific key-value pair:

```bash
jsondiff https://api.example.com/data --filter-key "status" --filter-value "active"
```

Filter by key only (shows all items with that key):

```bash
jsondiff https://api.example.com/data --filter-key "id"
```

### Show Only Differences

Display only the changes, not the full comparison:

```bash
jsondiff https://api.example.com/data --show-only-diffs
```

### Custom Interval

Change the polling interval (default is 2 seconds):

```bash
jsondiff https://api.example.com/data -i 5
```

### With Authentication

Add custom HTTP headers for authentication:

```bash
jsondiff https://api.example.com/data --header "Authorization: Bearer your-token-here"
```

Multiple headers:

```bash
jsondiff https://api.example.com/data \
  --header "Authorization: Bearer token" \
  --header "X-Custom-Header: value"
```

### Complete Example

Monitor an API endpoint, filter for active items, show only diffs, and poll every 3 seconds:

```bash
jsondiff https://api.example.com/data \
  --filter-key "status" \
  --filter-value "active" \
  --show-only-diffs \
  -i 3 \
  --header "Authorization: Bearer token123"
```

## Command-Line Options

- `url` - URL to fetch JSON from (required)
- `-i, --interval` - Polling interval in seconds (default: 2.0)
- `--filter-path` - JSONPath-like path to filter (e.g., `"items[*]"` or `"data.items[0]"`)
- `--filter-key` - Key to filter objects by (e.g., `"id"`, `"status"`)
- `--filter-value` - Value to match for filter-key (optional)
- `--show-only-diffs` - Show only the differences, not full comparison
- `--header` - HTTP header to send (can be used multiple times, format: `"Key: Value"`)

## How It Works

1. Fetches JSON from the specified URL at the configured interval
2. Compares the current JSON with the previous version using DeepDiff
3. Applies any filters (path, key, or key-value) before comparison
4. Displays differences with colorized output:
   - 🟢 Green for added items
   - 🔴 Red for removed items
   - 🟡 Yellow for changed values
5. Saves the current state to `~/.jsondiff_cache/` for persistence across restarts

## Output Format

The tool displays:
- **Initial Load**: Shows the first fetched JSON with syntax highlighting
- **No Changes**: Shows a dimmed "No changes detected" message
- **With Changes**: Shows either:
  - **Full Comparison**: Side-by-side table of previous vs current JSON
  - **Diff Only**: Summary of changes (added, removed, modified items)

Press `Ctrl+C` to stop monitoring.
