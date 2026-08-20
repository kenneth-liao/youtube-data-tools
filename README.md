# YouTube Data Tools

A powerful CLI tool for working with the YouTube Data API.

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
