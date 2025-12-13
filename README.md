# YouTube Data Tools

A powerful CLI tool for working with the YouTube Data API.

## Requirements

This CLI tool requires [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management. You must install uv before using this tool.

## Installation

```bash
uv tool install https://github.com/kenneth-liao/youtube-data-tools.git
```

This will install the CLI as a uv tool which can then be ran from anywhere. This makes it easily accssible from any of your AI agents (Claude, Codex, Gemini, etc.) while only having to configure it once!

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

## Usage

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
