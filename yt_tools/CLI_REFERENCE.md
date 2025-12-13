# YouTube Toolbox CLI Reference

A command-line interface for interacting with the YouTube Data API.

## Global Options

- `-h, --help`: Show help message
- `-v, --version`: Show version number

## Commands

### `search`
Search for videos on YouTube.

**Usage:**
```bash
youtube-toolbox search <query> [options]
```

**Arguments:**
- `query`: The search term(s)

**Options:**
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
youtube-toolbox details <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `--json`: Output results in JSON format

---

### `channel`
Get detailed information about a YouTube channel.

**Usage:**
```bash
youtube-toolbox channel <channel_id> [options]
```

**Arguments:**
- `channel_id`: YouTube Channel ID or URL

**Options:**
- `--json`: Output results in JSON format

---

### `transcript`
Get the transcript/captions for a video.

**Usage:**
```bash
youtube-toolbox transcript <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `--language <code>`: Language code (e.g., 'en', 'ko')
- `--json`: Output results in JSON format

---

### `comments`
Get top-level comments for a video.

**Usage:**
```bash
youtube-toolbox comments <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `--max-results <int>`: Maximum number of comments (default: 20)
- `--order <type>`: Sort order (time, relevance) - default: relevance
- `--replies`: Include replies in the output
- `--json`: Output results in JSON format

---

### `related`
Get videos related to a specific video.

**Usage:**
```bash
youtube-toolbox related <video_id> [options]
```

**Arguments:**
- `video_id`: YouTube Video ID or URL

**Options:**
- `--max-results <int>`: Maximum number of results (default: 10)
- `--json`: Output results in JSON format

---

### `trending`
Get current trending videos for a region.

**Usage:**
```bash
youtube-toolbox trending [options]
```

**Options:**
- `--region <code>`: Region code (ISO 3166-1 alpha-2) - default: US
- `--max-results <int>`: Maximum number of results (default: 10)
- `--json`: Output results in JSON format

---

### `docs`
Show this full documentation.

**Usage:**
```bash
youtube-toolbox docs
```
