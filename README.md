# YouTube Data Tools

A CLI for public YouTube data and authorized private channel analytics.

## Requirements

This CLI tool requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management. You must install uv before using this tool.

## Installation

```bash
uv tool install https://github.com/kenneth-liao/youtube-data-tools.git
```

This will install the CLI as a uv tool which can then be ran from anywhere. This makes it easily accssible from any of your AI agents (Claude, Codex, Gemini, etc.) while only having to configure it once!

## Updating

```bash
uv tool update yt-tools
```

Or to force update:

```bash
uv tool install --force https://github.com/kenneth-liao/youtube-data-tools.git
```

## Setup

1.  Get a YouTube Data API key from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2.  Set your API key:

    ```bash
    export YOUTUBE_API_KEY='your-key-here'
    ```

    Or create a `.env` file in your current directory:

    ```
    YOUTUBE_API_KEY=your-key-here
    ```

    By default, the CLI will look for a `.env` file in the current directory and then ~/.claude/ if it can't find one in the current directory.

## Channel-owner authorization

Authorize private analytics access with a Google OAuth desktop client-secret file:

```bash
yt-tools authorize --client-secrets /path/to/client_secret.json
```

The command requests read-only YouTube and Analytics access. It stores a private
copy of the client configuration and a refreshable token in the operating
system's per-user `yt-tools` application-data directory. To select explicit
storage destinations for automation:

```bash
yt-tools authorize \
  --client-secrets /source/client_secret.json \
  --client-config-file /secure/yt-tools/client_secret.json \
  --token-file /secure/yt-tools/token.json
```

OAuth files are not discovered from project directories, `.env`, `~/.claude`,
or `yutu` locations. Do not commit client-secret or token files.

## Query channel analytics

Run a synchronous analytics query after authorization:

```bash
yt-tools analytics query \
  --channel MINE \
  --start-date 2026-08-01 \
  --end-date 2026-08-18 \
  --metrics views,estimatedMinutesWatched \
  --dimensions day \
  --sort day
```

Use an owned channel ID instead of `MINE` when needed. Additional optional
upstream parameters are `--filters`, `--max-results`, `--start-index`, and
`--currency`. Use `--token-file` to select an explicit stored authorization.
For descending sorting, pass the value with an equals sign, such as
`--sort=-views`.

The command returns JSON by default, with the requested range, the returned
range when it can be derived from `day` rows, ordered column metadata, and rows
keyed by column name. Use `--format csv` to emit the same query result as CSV;
headers follow the returned column order, and an empty successful query emits
headers only. A successful empty JSON result has an empty `rows` array and a
`null` returned range. Google determines which metrics, dimensions, and filters
are compatible.

For a query with the `video` dimension, explicitly request current video
metadata through the authorized YouTube Data API:

```bash
yt-tools analytics query \
  --channel MINE \
  --start-date 2026-08-01 \
  --end-date 2026-08-18 \
  --metrics views \
  --dimensions video \
  --enrich-video-metadata
```

Each row keeps its canonical `video` ID and gains `videoMetadata`. Available
metadata includes current snippet, content details, and status. A missing,
deleted, or inaccessible video has `{"availability": "unavailable"}` instead.
Without this option, no Data API metadata request occurs and the result contract
is unchanged. In CSV output, `videoMetadata` is a JSON value in its own column.

## Retrieve a performance snapshot

Retrieve the authorized channel's predefined performance view:

```bash
yt-tools analytics snapshot --channel MINE
```

Without dates, the snapshot requests the previous 28 completed reporting days
in YouTube's Pacific-time calendar, ending yesterday. Override the range by
providing both dates:

```bash
yt-tools analytics snapshot \
  --channel MINE \
  --start-date 2026-08-01 \
  --end-date 2026-08-18
```

Select one owned video with `--video <video-id>`. Video snapshots automatically
include current authorized Data API metadata while preserving the selected
video ID:

```bash
yt-tools analytics snapshot --channel MINE --video dQw4w9WgXcQ
```

Channel snapshots include views, estimated watch minutes, average view duration,
average percentage viewed, and subscribers gained and lost. Video snapshots
omit subscriber metrics because YouTube does not support them for that target.
The command gets period totals and averages from an aggregate Analytics API
query and daily trends from a separate `day` query; it does not calculate
aggregates from daily values.

By default, the snapshot also retrieves the immediately preceding period with
the same inclusive day count. The `comparison` object keeps that period's
requested range, returned range, aggregate values, and daily rows separate from
the current period. The `changes` object gives each comparable metric's
`absolute` change (`current - preceding`) and `percentage` change
(`(current - preceding) / preceding * 100`). Percentage is `null` when the
preceding value is zero or absent. Use `--no-comparison` to omit comparison output and
skip both preceding-period API requests.

JSON output identifies each requested range and the actual range represented by
its daily rows. Processing delays can make these ranges differ. An empty period
has `null` period values, an empty daily row array, and a `null` returned range;
the command does not create zero values or prose analysis.

## Discover available reporting types

List the asynchronous Reporting API report types available to the authorized
channel:

```bash
yt-tools reporting report-types
```

Use `--token-file` to select an explicit stored authorization. The JSON result
preserves each upstream report type ID, name, optional deprecation time, and
system-managed status. `isReachReport` identifies reach report types from their
upstream names, so selection does not depend on a versioned report type ID.
Pagination is automatic.

A successful response uses `availability: "available"` with selectable report
types or `availability: "empty"` with an empty list and explanatory message.
Authorization and Reporting API failures instead return a nonzero exit status
with actionable details.

## Manage asynchronous reporting jobs

Create a reporting job from an available report type ID and caller-selected
name:

```bash
yt-tools reporting jobs create \
  --report-type-id channel_basic_a3 \
  --name "Daily channel export"
```

Creation returns the upstream job ID, report type ID, name, and creation time.
List existing jobs and their upstream lifecycle metadata:

```bash
yt-tools reporting jobs list
```

Delete one selected job explicitly by its stable upstream identity:

```bash
yt-tools reporting jobs delete --job-id <job-id>
```

Successful deletion returns the selected ID with `status: "deleted"`. List all
generated reporting files for a selected job:

```bash
yt-tools reporting jobs reports list --job-id <job-id>
```

The command follows every response page and preserves each report's upstream
ID, job ID, covered start and end times, creation time, and authenticated
download URL. Files for the same period remain distinct, so later backfills are
visible. A valid job with no generated files returns explicit empty availability
rather than an error.

An absent or unauthorized job, invalid report type, or other Reporting API
failure returns a nonzero status with the upstream HTTP status and actionable
details. All job commands support `--token-file` for an explicit stored
authorization. They do not download or aggregate file contents, perform
reach-specific orchestration, or wait for YouTube to generate a reporting file.

## Usage

Each subcommand also supports a `-h` or `--help` option for detailed usage information (e.g., `yt-tools search -h`).

```bash
# Search for videos
yt-tools search "python tutorials"

# Get video details
yt-tools details <video_id>

# Get video transcript
yt-tools transcript <video_id>

# Get channel stats
yt-tools channel <channel_id>
```

## Development

1.  Clone the repository.
2.  Install dependencies:

    ```bash
    uv sync
    ```

3.  Run the CLI:

    ```bash
    uv run yt-tools --help
    ```
