import argparse
import csv
import json
import os
import sys
from importlib import metadata
from typing import List, Optional, Any
from dotenv import load_dotenv, find_dotenv

from yt_tools.analytics import (
    AnalyticsInputError,
    AnalyticsQuery,
    AnalyticsQueryError,
    build_analytics_api,
    query_channel_analytics,
)
from yt_tools.auth import (
    AuthorizationError,
    authorize,
    load_authorized_credentials,
    resolve_credential_paths,
)
from yt_tools.core import YouTubeService
from yt_tools.reporting import (
    ReportingError,
    build_reporting_api,
    create_reporting_job,
    delete_reporting_job,
    list_reporting_jobs,
    list_report_types,
)
from yt_tools.snapshot import (
    create_analytics_snapshot,
    resolve_snapshot_range,
    validate_snapshot_target,
)
from yt_tools.video_metadata import (
    VideoMetadataError,
    build_data_api,
    enrich_video_rows,
)

def _load_api_key_environment() -> None:
    """Load legacy API-key locations for public Data API commands only."""
    load_dotenv(find_dotenv(usecwd=True))
    if not os.environ.get("YOUTUBE_API_KEY"):
        claude_env_path = os.path.join(os.path.expanduser("~"), ".claude", ".env")
        if os.path.exists(claude_env_path):
            load_dotenv(claude_env_path, override=True)


def get_version() -> str:
    """Get the package version from metadata."""
    try:
        return metadata.version("youtube-data-tools")
    except metadata.PackageNotFoundError:
        return "0.0.0-dev"

class ToolboxError(Exception):
    """Base exception for toolbox CLI errors with helpful messages."""
    pass

def _get_service() -> YouTubeService:
    """Initialize and return the YouTube Service."""
    try:
        _load_api_key_environment()
        return YouTubeService()
    except ValueError as e:
        raise ToolboxError(
            f"ERROR: {str(e)}\n\n"
            f"SOLUTION: Set your YouTube Data API key in one of these ways:\n"
            f"  1. Create a .env file in your current directory:\n"
            f"     echo 'YOUTUBE_API_KEY=your-key-here' > .env\n\n"
            f"  2. Export as environment variable:\n"
            f"     export YOUTUBE_API_KEY='your-key-here'\n\n"
            f"Get your API key at: https://console.cloud.google.com/apis/credentials"
        )
    except Exception as e:
        raise ToolboxError(f"ERROR: Failed to initialize YouTube Service: {e}")

def print_json(data: Any):
    """Print data as JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def print_analytics_csv(result: dict) -> None:
    """Print an analytics query result as CSV."""
    names = [column["name"] for column in result["columns"]]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(names)
    writer.writerows(
        [
            json.dumps(row[name], ensure_ascii=False, separators=(",", ":"))
            if isinstance(row[name], (dict, list))
            else row[name]
            for name in names
        ]
        for row in result["rows"]
    )


def cmd_search(args: argparse.Namespace) -> int:
    service = _get_service()
    
    options = {}
    if args.channel_id:
        options['channelId'] = args.channel_id
    if args.order:
        options['order'] = args.order
    if args.duration:
        options['videoDuration'] = args.duration
    
    try:
        results = service.search_videos(args.query, args.max_results, **options)
        
        # Format for display unless --json is used
        if args.json:
            print_json(results)
        else:
            items = results.get('items', [])
            if not items:
                print("No videos found.")
                return 0
                
            print(f"Found {len(items)} videos for '{args.query}':\n")
            for item in items:
                video_id = item.get('id', {}).get('videoId')
                if not video_id: continue # Skip if not a video (e.g. channel) 
                
                title = item.get('snippet', {}).get('title')
                channel = item.get('snippet', {}).get('channelTitle')
                print(f"- {title} (ID: {video_id})")
                print(f"  Channel: {channel}")
                print(f"  URL: https://www.youtube.com/watch?v={video_id}")
                print()
                
    except Exception as e:
        raise ToolboxError(f"Error searching videos: {e}")
    return 0

def cmd_details(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        results = service.get_video_details(args.video_id)
        if not results.get('items'):
            raise ToolboxError(f"Video with ID {args.video_id} not found.")
            
        if args.json:
            print_json(results)
        else:
            video = results['items'][0]
            snippet = video.get('snippet', {})
            stats = video.get('statistics', {})
            
            print(f"Title: {snippet.get('title')}")
            print(f"Channel: {snippet.get('channelTitle')}")
            print(f"Published: {snippet.get('publishedAt')}")
            print(f"Views: {stats.get('viewCount')}")
            print(f"Likes: {stats.get('likeCount')}")
            print(f"Description:\n{snippet.get('description')}")
            
    except Exception as e:
        raise ToolboxError(f"Error getting details: {e}")
    return 0

def cmd_channel(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        results = service.get_channel_details(args.channel_id)
        if not results.get('items'):
            raise ToolboxError(f"Channel with ID {args.channel_id} not found.")
            
        if args.json:
            print_json(results)
        else:
            channel = results['items'][0]
            snippet = channel.get('snippet', {})
            stats = channel.get('statistics', {})
            
            print(f"Title: {snippet.get('title')}")
            print(f"Description: {snippet.get('description')}")
            print(f"Subscribers: {stats.get('subscriberCount')}")
            print(f"Total Videos: {stats.get('videoCount')}")
            print(f"Total Views: {stats.get('viewCount')}")
            
    except Exception as e:
        raise ToolboxError(f"Error getting channel details: {e}")
    return 0

def cmd_transcript(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        transcript = service.get_video_transcript(args.video_id, args.language)
        if not transcript:
             raise ToolboxError(f"No transcript found for video {args.video_id} (lang: {args.language or 'default'}).")

        if args.json:
            # We construct a slightly richer JSON object
            output = {
                "videoId": args.video_id,
                "language": args.language,
                "transcript": transcript
            }
            print_json(output)
        else:
            print(f"Transcript for {args.video_id}:\n")
            for segment in transcript:
                text = getattr(segment, 'text', '') if not isinstance(segment, dict) else segment.get('text', '')
                start = getattr(segment, 'start', 0) if not isinstance(segment, dict) else segment.get('start', 0)
                timestamp = service.format_time(int(start * 1000))
                print(f"[{timestamp}] {text}")

    except Exception as e:
        raise ToolboxError(f"Error getting transcript: {e}")
    return 0

def cmd_comments(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        results = service.get_video_comments(
            args.video_id, 
            args.max_results, 
            order=args.order, 
            includeReplies=args.replies
        )
        
        if args.json:
            print_json(results)
        else:
            items = results.get('items', [])
            print(f"Comments for video {args.video_id} ({len(items)} shown):\n")
            for item in items:
                comment = item.get('snippet', {}).get('topLevelComment', {}).get('snippet', {})
                author = comment.get('authorDisplayName')
                text = comment.get('textDisplay')
                print(f"[{author}]: {text}")
                if args.replies and 'replies' in item:
                    for reply in item.get('replies', {}).get('comments', []):
                         r_snippet = reply.get('snippet', {})
                         print(f"  -> [{r_snippet.get('authorDisplayName')}]: {r_snippet.get('textDisplay')}")
                print("-" * 20)

    except Exception as e:
        raise ToolboxError(f"Error getting comments: {e}")
    return 0

def cmd_related(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        results = service.get_related_videos(args.video_id, args.max_results)
        
        if args.json:
            print_json(results)
        else:
            items = results.get('items', [])
            print(f"Related videos to {args.video_id}:\n")
            for item in items:
                # Related videos structure might be slightly different depending on the endpoint used in core
                # The core implementation uses search, so structure is search result like
                video_id = item.get('id', {}).get('videoId')
                if not video_id: continue
                
                title = item.get('snippet', {}).get('title')
                channel = item.get('snippet', {}).get('channelTitle')
                print(f"- {title} (ID: {video_id})")
                print(f"  Channel: {channel}")
                print()

    except Exception as e:
         raise ToolboxError(f"Error getting related videos: {e}")
    return 0

def cmd_trending(args: argparse.Namespace) -> int:
    service = _get_service()
    try:
        results = service.get_trending_videos(args.region, args.max_results)
        
        if args.json:
            print_json(results)
        else:
            items = results.get('items', [])
            print(f"Trending videos in {args.region or 'US'} ({len(items)} shown):\n")
            for item in items:
                title = item.get('snippet', {}).get('title')
                video_id = item.get('id')
                view_count = item.get('statistics', {}).get('viewCount')
                print(f"- {title} (ID: {video_id})")
                print(f"  Views: {view_count}")
                print()

    except Exception as e:
        raise ToolboxError(f"Error getting trending videos: {e}")
    return 0

def cmd_authorize(args: argparse.Namespace) -> int:
    """Authorize access to an owned YouTube channel."""
    paths = resolve_credential_paths(args.client_config_file, args.token_file)
    try:
        authorize(args.client_secrets, paths.client_config_file, paths.token_file)
    except AuthorizationError as error:
        raise ToolboxError(str(error)) from error
    print(f"Authorization complete. Credentials stored in {paths.token_file.parent}")
    return 0


def _build_authorized_reporting_api(token_file: str | None):
    resolved_token = resolve_credential_paths(token_file=token_file).token_file
    credentials = load_authorized_credentials(resolved_token)
    return build_reporting_api(credentials)


def cmd_reporting_report_types(args: argparse.Namespace) -> int:
    """List Reporting API report types available to the authorized channel."""
    try:
        result = list_report_types(_build_authorized_reporting_api(args.token_file))
    except (AuthorizationError, ReportingError) as error:
        raise ToolboxError(str(error)) from error
    print_json(result)
    return 0


def cmd_reporting_job_create(args: argparse.Namespace) -> int:
    """Create an asynchronous reporting job without waiting for files."""
    try:
        result = create_reporting_job(
            _build_authorized_reporting_api(args.token_file),
            args.report_type_id,
            args.name,
        )
    except (AuthorizationError, ReportingError) as error:
        raise ToolboxError(str(error)) from error
    print_json(result)
    return 0


def cmd_reporting_jobs_list(args: argparse.Namespace) -> int:
    """List asynchronous reporting jobs without accessing generated files."""
    try:
        result = list_reporting_jobs(
            _build_authorized_reporting_api(args.token_file)
        )
    except (AuthorizationError, ReportingError) as error:
        raise ToolboxError(str(error)) from error
    print_json(result)
    return 0


def cmd_reporting_job_delete(args: argparse.Namespace) -> int:
    """Delete one asynchronous reporting job by upstream identity."""
    try:
        result = delete_reporting_job(
            _build_authorized_reporting_api(args.token_file), args.job_id
        )
    except (AuthorizationError, ReportingError) as error:
        raise ToolboxError(str(error)) from error
    print_json(result)
    return 0


def cmd_analytics_query(args: argparse.Namespace) -> int:
    """Run a synchronous analytics query for an authorized channel."""
    try:
        query = AnalyticsQuery(
            channel=args.channel,
            start_date=args.start_date,
            end_date=args.end_date,
            metrics=args.metrics,
            dimensions=args.dimensions,
            filters=args.filters,
            sort=args.sort,
            max_results=args.max_results,
            start_index=args.start_index,
            currency=args.currency,
        )
        if args.enrich_video_metadata and "video" not in (
            query.dimensions or ""
        ).split(","):
            raise AnalyticsInputError(
                "--enrich-video-metadata requires the video dimension."
            )
        token_file = resolve_credential_paths(token_file=args.token_file).token_file
        credentials = load_authorized_credentials(token_file)
        result = query_channel_analytics(build_analytics_api(credentials), query)
        if args.enrich_video_metadata:
            result = enrich_video_rows(build_data_api(credentials), result)
    except (
        AnalyticsInputError,
        AnalyticsQueryError,
        AuthorizationError,
        VideoMetadataError,
    ) as error:
        raise ToolboxError(str(error)) from error
    if args.format == "csv":
        print_analytics_csv(result)
    else:
        print_json(result)
    return 0


def cmd_analytics_snapshot(args: argparse.Namespace) -> int:
    """Retrieve a predefined performance view for an authorized channel or video."""
    try:
        start_date, end_date = resolve_snapshot_range(args.start_date, args.end_date)
        channel = validate_snapshot_target(args.channel, args.video)
        token_file = resolve_credential_paths(token_file=args.token_file).token_file
        credentials = load_authorized_credentials(token_file)
        result = create_analytics_snapshot(
            build_analytics_api(credentials),
            channel=channel,
            start_date=start_date,
            end_date=end_date,
            video=args.video,
            data_api=build_data_api(credentials) if args.video else None,
            comparison_enabled=not args.no_comparison,
        )
    except (
        AnalyticsInputError,
        AnalyticsQueryError,
        AuthorizationError,
        VideoMetadataError,
    ) as error:
        raise ToolboxError(str(error)) from error
    print_json(result)
    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    """Display full CLI documentation from CLI_REFERENCE.md."""
    try:
        # Get the directory where cli.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        doc_path = os.path.join(current_dir, "CLI_REFERENCE.md")
        
        with open(doc_path, "r", encoding="utf-8") as f:
            print(f.read())
        return 0
    except Exception as e:
        raise ToolboxError(f"Error reading documentation: {e}")

CONCISE_DOCS = """
YouTube Data Tools CLI Reference

Usage: yt-tools <command> [arguments]

For detailed help on any command, use `yt-tools <command> -h`.

Commands:
  search       Search for videos
  details      Get video details
  channel      Get channel details
  transcript   Get video transcript
  comments     Get video comments
  related      Get related videos
  trending     Get trending videos
  authorize    Authorize access to an owned YouTube channel
  analytics    Query analytics or retrieve a performance snapshot
  reporting    Discover asynchronous reporting resources
  docs         Show full documentation

Environment Variables:
  YOUTUBE_API_KEY  Required. Your Google Data API key.

Examples:
  yt-tools search "python tutorials" --max-results 5
  yt-tools details <video_id>
  yt-tools transcript <video_id> --language en
"""

COMMAND_DOCS = {
    "search": """
Search for videos on YouTube.

Usage:
  yt-tools search <query> [options]

Arguments:
  query           The search term(s)

Options:
  --max-results <int>   Maximum number of results to return (default: 10)
  --channel-id <id>     Filter results by channel ID
  --order <type>        Sort order (date, rating, relevance, title, videoCount, viewCount)
  --duration <type>     Filter by duration (any, long, medium, short)
  --json                Output results in JSON format
""",
    "details": """
Get detailed information about a specific video.

Usage:
  yt-tools details <video_id> [options]

Arguments:
  video_id        YouTube Video ID or URL

Options:
  --json          Output results in JSON format
""",
    "channel": """
Get detailed information about a YouTube channel.

Usage:
  yt-tools channel <channel_id> [options]

Arguments:
  channel_id      YouTube Channel ID or URL

Options:
  --json          Output results in JSON format
""",
    "transcript": """
Get the transcript/captions for a video.

Usage:
  yt-tools transcript <video_id> [options]

Arguments:
  video_id        YouTube Video ID or URL

Options:
  --language <code>     Language code (e.g., 'en', 'ko')
  --json                Output results in JSON format
""",
    "comments": """
Get top-level comments for a video.

Usage:
  yt-tools comments <video_id> [options]

Arguments:
  video_id        YouTube Video ID or URL

Options:
  --max-results <int>   Maximum number of comments (default: 20)
  --order <type>        Sort order (time, relevance) - default: relevance
  --replies             Include replies in the output
  --json                Output results in JSON format
""",
    "related": """
Get videos related to a specific video.

Usage:
  yt-tools related <video_id> [options]

Arguments:
  video_id        YouTube Video ID or URL

Options:
  --max-results <int>   Maximum number of results (default: 10)
  --json                Output results in JSON format
""",
    "trending": """
Get current trending videos for a region.

Usage:
  yt-tools trending [options]

Options:
  --region <code>       Region code (ISO 3166-1 alpha-2) - default: US
  --max-results <int>   Maximum number of results (default: 10)
  --json                Output results in JSON format
""",
    "authorize": """
Authorize access to an owned YouTube channel.

Usage:
  yt-tools authorize --client-secrets <source> [options]

Options:
  --client-secrets <path>       Google OAuth client-secret source file (required)
  --client-config-file <path>   Stored client configuration destination
  --token-file <path>           Stored refreshable token destination
""",
    "reporting": """
Discover asynchronous reporting resources for an authorized channel.

Usage:
  yt-tools reporting report-types [options]
  yt-tools reporting jobs create --report-type-id <id> --name <name> [options]
  yt-tools reporting jobs list [options]
  yt-tools reporting jobs delete --job-id <id> [options]
""",
    "reporting-report-types": """
List YouTube Reporting API report types available to the authorized channel.

Usage:
  yt-tools reporting report-types [options]

Optional parameters:
  --token-file <path>           Stored authorization override
""",
    "reporting-jobs": """
Create, list, or delete asynchronous reporting jobs.

Usage:
  yt-tools reporting jobs create --report-type-id <id> --name <name> [options]
  yt-tools reporting jobs list [options]
  yt-tools reporting jobs delete --job-id <id> [options]
""",
    "reporting-jobs-create": """
Create an asynchronous reporting job.

Required options:
  --report-type-id <id>         Available upstream report type ID
  --name <name>                 Caller-selected job name

Optional parameters:
  --token-file <path>           Stored authorization override
""",
    "reporting-jobs-list": """
List asynchronous reporting jobs with stable IDs and lifecycle metadata.

Optional parameters:
  --token-file <path>           Stored authorization override
""",
    "reporting-jobs-delete": """
Delete one asynchronous reporting job by upstream identity.

Required options:
  --job-id <id>                 Upstream reporting job ID

Optional parameters:
  --token-file <path>           Stored authorization override
""",
    "analytics": """
Retrieve analytics for an authorized channel.

Usage:
  yt-tools analytics query [options]
  yt-tools analytics snapshot [options]
""",
    "analytics-query": """
Run a synchronous YouTube Analytics API v2 channel query.

Required options:
  --channel <MINE|channel-id>   Authorized channel identity
  --start-date <YYYY-MM-DD>     First requested reporting day
  --end-date <YYYY-MM-DD>       Last requested reporting day
  --metrics <names>             Comma-separated metric names

Optional parameters:
  --dimensions <names>          Comma-separated dimension names
  --filters <expression>        Analytics API filter expression
  --sort <names>                Comma-separated sort fields
  --max-results <int>           Maximum rows to return
  --start-index <int>           One-based first row
  --currency <code>             Currency for monetary metrics
  --token-file <path>           Stored authorization override
  --format <json|csv>           Output format (default: json)
  --enrich-video-metadata       Add current metadata to video-dimension rows
""",
    "analytics-snapshot": """
Retrieve a predefined performance view for an authorized channel or owned video.

Required options:
  --channel <MINE|channel-id>   Authorized channel identity

Optional parameters:
  --video <video-id>            Select one owned video
  --start-date <YYYY-MM-DD>     First requested reporting day
  --end-date <YYYY-MM-DD>       Last requested reporting day
  --token-file <path>           Stored authorization override
  --no-comparison               Skip the preceding-period comparison
""",
    "docs": """
Show the full documentation.

Usage:
  yt-tools docs
"""
}

def _non_empty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("value must not be empty")
    return value


class CustomHelpParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.custom_help_text = kwargs.pop('custom_help_text', None)
        super().__init__(*args, **kwargs)

    def format_help(self):
        if self.custom_help_text:
            return self.custom_help_text
        return super().format_help()

def build_parser() -> argparse.ArgumentParser:
    # Use our custom parser for the main entry point to override --help output
    p = CustomHelpParser(
        "yt-tools",
        description="YouTube Data Tools CLI (MCP Compatible)",
        add_help=False,
        custom_help_text=CONCISE_DOCS
    )
    
    p.add_argument(
        "-v", "--version",
        action="version",
        version=f"yt-tools {get_version()}"
    )
    p.add_argument(
        "-h", "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit"
    )

    # Use CustomHelpParser for subcommands so they can also have custom help text
    sub = p.add_subparsers(dest="cmd", required=False, parser_class=CustomHelpParser)

    # Search
    s = sub.add_parser("search", help="Search for YouTube videos", custom_help_text=COMMAND_DOCS["search"])
    s.add_argument("query", help="Search query")
    s.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    s.add_argument("--channel-id", help="Filter by channel ID")
    s.add_argument("--order", choices=['date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'], help="Sort order")
    s.add_argument("--duration", choices=['any', 'long', 'medium', 'short'], help="Filter by duration")
    s.add_argument("--json", action="store_true", help="Output JSON")
    s.set_defaults(func=cmd_search)

    # Details
    d = sub.add_parser("details", help="Get video details", custom_help_text=COMMAND_DOCS["details"])
    d.add_argument("video_id", help="YouTube Video ID or URL")
    d.add_argument("--json", action="store_true", help="Output JSON")
    d.set_defaults(func=cmd_details)

    # Channel
    c = sub.add_parser("channel", help="Get channel details", custom_help_text=COMMAND_DOCS["channel"])
    c.add_argument("channel_id", help="YouTube Channel ID or URL")
    c.add_argument("--json", action="store_true", help="Output JSON")
    c.set_defaults(func=cmd_channel)

    # Transcript
    t = sub.add_parser("transcript", help="Get video transcript", custom_help_text=COMMAND_DOCS["transcript"])
    t.add_argument("video_id", help="YouTube Video ID or URL")
    t.add_argument("--language", help="Language code (e.g., 'en', 'ko')")
    t.add_argument("--json", action="store_true", help="Output JSON")
    t.set_defaults(func=cmd_transcript)

    # Comments
    cm = sub.add_parser("comments", help="Get video comments", custom_help_text=COMMAND_DOCS["comments"])
    cm.add_argument("video_id", help="YouTube Video ID or URL")
    cm.add_argument("--max-results", type=int, default=20, help="Max comments (default: 20)")
    cm.add_argument("--order", choices=['time', 'relevance'], default='relevance', help="Order by")
    cm.add_argument("--replies", action="store_true", help="Include replies")
    cm.add_argument("--json", action="store_true", help="Output JSON")
    cm.set_defaults(func=cmd_comments)

    # Related
    r = sub.add_parser("related", help="Get related videos", custom_help_text=COMMAND_DOCS["related"])
    r.add_argument("video_id", help="YouTube Video ID or URL")
    r.add_argument("--max-results", type=int, default=10, help="Max results")
    r.add_argument("--json", action="store_true", help="Output JSON")
    r.set_defaults(func=cmd_related)

    # Trending
    tr = sub.add_parser("trending", help="Get trending videos", custom_help_text=COMMAND_DOCS["trending"])
    tr.add_argument("--region", default="US", help="Region code (default: US)")
    tr.add_argument("--max-results", type=int, default=10, help="Max results")
    tr.add_argument("--json", action="store_true", help="Output JSON")
    tr.set_defaults(func=cmd_trending)

    # Authorization
    auth = sub.add_parser(
        "authorize",
        help="Authorize access to an owned YouTube channel",
        custom_help_text=COMMAND_DOCS["authorize"],
    )
    auth.add_argument("--client-secrets", required=True, help="Google OAuth client-secret source file")
    auth.add_argument("--client-config-file", help="Stored client configuration destination")
    auth.add_argument("--token-file", help="Stored refreshable token destination")
    auth.set_defaults(func=cmd_authorize)

    # Analytics
    analytics = sub.add_parser(
        "analytics",
        help="Query analytics or retrieve a performance snapshot",
        custom_help_text=COMMAND_DOCS["analytics"],
    )
    analytics_sub = analytics.add_subparsers(
        dest="analytics_cmd",
        required=True,
        parser_class=CustomHelpParser,
    )
    analytics_query = analytics_sub.add_parser(
        "query",
        help="Run a synchronous channel analytics query",
        custom_help_text=COMMAND_DOCS["analytics-query"],
    )
    analytics_query.add_argument("--channel", required=True)
    analytics_query.add_argument("--start-date", required=True)
    analytics_query.add_argument("--end-date", required=True)
    analytics_query.add_argument("--metrics", required=True)
    analytics_query.add_argument("--dimensions")
    analytics_query.add_argument("--filters")
    analytics_query.add_argument("--sort")
    analytics_query.add_argument("--max-results", type=int)
    analytics_query.add_argument("--start-index", type=int)
    analytics_query.add_argument("--currency")
    analytics_query.add_argument("--token-file")
    analytics_query.add_argument("--format", choices=("json", "csv"), default="json")
    analytics_query.add_argument("--enrich-video-metadata", action="store_true")
    analytics_query.set_defaults(func=cmd_analytics_query)

    analytics_snapshot = analytics_sub.add_parser(
        "snapshot",
        help="Retrieve a channel or video performance snapshot",
        custom_help_text=COMMAND_DOCS["analytics-snapshot"],
    )
    analytics_snapshot.add_argument("--channel", required=True)
    analytics_snapshot.add_argument("--video")
    analytics_snapshot.add_argument("--start-date")
    analytics_snapshot.add_argument("--end-date")
    analytics_snapshot.add_argument("--token-file")
    analytics_snapshot.add_argument("--no-comparison", action="store_true")
    analytics_snapshot.set_defaults(func=cmd_analytics_snapshot)

    # Reporting
    reporting = sub.add_parser(
        "reporting",
        help="Discover asynchronous reporting resources",
        custom_help_text=COMMAND_DOCS["reporting"],
    )
    reporting_sub = reporting.add_subparsers(
        dest="reporting_cmd",
        required=True,
        parser_class=CustomHelpParser,
    )
    reporting_report_types = reporting_sub.add_parser(
        "report-types",
        help="List report types available to the authorized channel",
        custom_help_text=COMMAND_DOCS["reporting-report-types"],
    )
    reporting_report_types.add_argument("--token-file")
    reporting_report_types.set_defaults(func=cmd_reporting_report_types)

    reporting_jobs = reporting_sub.add_parser(
        "jobs",
        help="Create, list, or delete asynchronous reporting jobs",
        custom_help_text=COMMAND_DOCS["reporting-jobs"],
    )
    reporting_jobs_sub = reporting_jobs.add_subparsers(
        dest="reporting_jobs_cmd",
        required=True,
        parser_class=CustomHelpParser,
    )
    reporting_jobs_create = reporting_jobs_sub.add_parser(
        "create",
        help="Create an asynchronous reporting job",
        custom_help_text=COMMAND_DOCS["reporting-jobs-create"],
    )
    reporting_jobs_create.add_argument(
        "--report-type-id", required=True, type=_non_empty
    )
    reporting_jobs_create.add_argument("--name", required=True, type=_non_empty)
    reporting_jobs_create.add_argument("--token-file")
    reporting_jobs_create.set_defaults(func=cmd_reporting_job_create)
    reporting_jobs_list = reporting_jobs_sub.add_parser(
        "list",
        help="List asynchronous reporting jobs",
        custom_help_text=COMMAND_DOCS["reporting-jobs-list"],
    )
    reporting_jobs_list.add_argument("--token-file")
    reporting_jobs_list.set_defaults(func=cmd_reporting_jobs_list)
    reporting_jobs_delete = reporting_jobs_sub.add_parser(
        "delete",
        help="Delete an asynchronous reporting job",
        custom_help_text=COMMAND_DOCS["reporting-jobs-delete"],
    )
    reporting_jobs_delete.add_argument("--job-id", required=True, type=_non_empty)
    reporting_jobs_delete.add_argument("--token-file")
    reporting_jobs_delete.set_defaults(func=cmd_reporting_job_delete)

    # Docs
    doc = sub.add_parser("docs", help="Display full documentation", custom_help_text=COMMAND_DOCS["docs"])
    doc.set_defaults(func=cmd_docs)

    return p

def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        if e.code != 0:
            print("\nHINT: Use --help to see all available options", file=sys.stderr)
        raise

    if not args.cmd:
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except ToolboxError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())