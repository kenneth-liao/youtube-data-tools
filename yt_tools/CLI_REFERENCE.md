# YouTube Data Tools CLI Reference

A command-line interface for interacting with the YouTube Data API.

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

### `docs`
Show this full documentation.

**Usage:**
```bash
yt-tools docs
```