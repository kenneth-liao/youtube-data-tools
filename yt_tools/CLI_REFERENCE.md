# YouTube Data Tools CLI Reference

A command-line interface for public YouTube data and authorized channel analytics.

## Global Options

- `-h, --help`: Show help message
- `-v, --version`: Show version number

## Commands

### `search`
Search for videos on YouTube.

**Usage:**
```bash
yt-tools search <query> [options]
```

**Arguments:**
- `query`: The search term(s)

**Options:**
- `-h, --help`: Show help message for the 'search' command
- `--max-results <int>`: Maximum number of results to return (default: 10)
- `--channel-id <id>`: Filter results by channel ID
- `--order <type>`: Sort order (date, rating, relevance, title, videoCount, viewCount)
- `--duration <type>`: Filter by duration (any, long, medium, short)
- `--json`: Output results in JSON format

---

### `details`
Get detailed information about a specific video.

**Usage:**
```bash
yt-tools details <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `-h, --help`: Show help message for the 'details' command
- `--json`: Output results in JSON format

---

### `channel`
Get detailed information about a YouTube channel.

**Usage:**
```bash
yt-tools channel <channel_id> [options]
```

**Arguments:**
- `channel_id`: YouTube Channel ID or URL

**Options:**
- `-h, --help`: Show help message for the 'channel' command
- `--json`: Output results in JSON format

---

### `transcript`
Get the transcript/captions for a video.

**Usage:**
```bash
yt-tools transcript <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `-h, --help`: Show help message for the 'transcript' command
- `--language <code>`: Language code (e.g., 'en', 'ko')
- `--json`: Output results in JSON format

---

### `comments`
Get top-level comments for a video.

**Usage:**
```bash
yt-tools comments <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `-h, --help`: Show help message for the 'comments' command
- `--max-results <int>`: Maximum number of comments (default: 20)
- `--order <type>`: Sort order (time, relevance) - default: relevance
- `--replies`: Include replies in the output
- `--json`: Output results in JSON format

---

### `related`
Get videos related to a specific video.

**Usage:**
```bash
yt-tools related <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `-h, --help`: Show help message for the 'related' command
- `--max-results <int>`: Maximum number of results (default: 10)
- `--json`: Output results in JSON format

---

### `trending`
Get current trending videos for a region.

**Usage:**
```bash
yt-tools trending [options]
```

**Options:**
- `-h, --help`: Show help message for the 'trending' command
- `--region <code>`: Region code (ISO 3166-1 alpha-2) - default: US
- `--max-results <int>`: Maximum number of results (default: 10)
- `--json`: Output results in JSON format

---

### `authorize`
Authorize access to an owned YouTube channel with a Google OAuth client-secret file.

**Usage:**
```bash
yt-tools authorize --client-secrets <source> [options]
```

**Options:**
- `--client-secrets <path>`: Required user-selected Google OAuth client-secret source file
- `--client-config-file <path>`: Stored canonical client configuration destination
- `--token-file <path>`: Stored refreshable token destination

Without destination overrides, credentials are stored with owner-only access in
the operating system's per-user `yt-tools` application-data directory.

---

### `analytics query`
Run a synchronous YouTube Analytics API v2 query for an authorized channel.

**Usage:**
```bash
yt-tools analytics query \
  --channel MINE \
  --start-date 2026-08-01 \
  --end-date 2026-08-18 \
  --metrics views,estimatedMinutesWatched \
  [options]
```

**Required options:**
- `--channel <MINE|channel-id>`: Authorized channel identity
- `--start-date <YYYY-MM-DD>`: First requested reporting day
- `--end-date <YYYY-MM-DD>`: Last requested reporting day
- `--metrics <names>`: Comma-separated metric names

**Optional parameters:**
- `--dimensions <names>`: Comma-separated dimension names
- `--filters <expression>`: Analytics API filter expression
- `--sort <names>`: Comma-separated sort fields; use `--sort=-views` for descending fields
- `--max-results <int>`: Maximum rows to return
- `--start-index <int>`: One-based first row for pagination
- `--currency <code>`: Currency for monetary metrics
- `--token-file <path>`: Stored authorization override
- `--format <json|csv>`: Output format (default: `json`)
- `--enrich-video-metadata`: Add current authorized Data API metadata to rows; requires the `video` dimension

JSON output contains requested and returned range metadata, ordered column
metadata, and rows keyed by column name. The returned range is `null` when it
cannot be derived from `day` rows. CSV output uses the returned column order for
headers and values; empty and null values are empty CSV fields. Empty successful
queries return an empty JSON `rows` array or header-only CSV. Metric, dimension,
and filter compatibility is determined by Google.

Metadata enrichment is explicit. Without the option, the query makes no Data
API metadata request and its result contract is unchanged. With the option,
each row keeps its canonical `video` ID and gains `videoMetadata` containing an
availability value and, when available, the current snippet, content details,
and status. Missing, deleted, and inaccessible videos are represented as
unavailable without dropping their analytics rows. CSV serializes this metadata
as JSON in the added column. A Data API request failure fails the command rather
than returning partial enrichment.

---

### `analytics snapshot`
Retrieve a predefined performance view for the authorized channel or one owned video.

**Usage:**
```bash
yt-tools analytics snapshot --channel MINE [options]
```

**Required options:**
- `--channel <MINE|channel-id>`: Authorized channel identity

**Optional parameters:**
- `--video <video-id>`: Select one owned video
- `--start-date <YYYY-MM-DD>`: First requested reporting day; requires `--end-date`
- `--end-date <YYYY-MM-DD>`: Last requested reporting day; requires `--start-date`
- `--token-file <path>`: Stored authorization override
- `--no-comparison`: Skip the preceding-period comparison and its API requests

Without explicit dates, the command requests the previous 28 completed
Pacific-time reporting days ending yesterday. Channel snapshots include views,
estimated watch minutes, average view duration, average percentage viewed, and
subscribers gained and lost. Video snapshots omit the incompatible subscriber
metrics and automatically include current Data API metadata while preserving
the selected video ID.

The JSON result contains the target, requested and actual returned ranges,
period values, and daily rows. By default, a separate `comparison` object
contains the requested range, returned range, period values, and daily rows for
the immediately preceding equal-length period. The `changes` object contains
each comparable metric's absolute change (`current - preceding`) and percentage
change (`(current - preceding) / preceding * 100`). An absent or zero preceding
value makes the percentage `null`.
Period totals and averages come from separate aggregate API queries rather than
calculations over daily values. An empty period uses `null` period values, an
empty daily row array, and a `null` returned range; it does not contain
fabricated zero values or prose analysis.

---

### `docs`
Show this full documentation.

**Usage:**
```bash
yt-tools docs
```