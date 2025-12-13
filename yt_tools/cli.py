import argparse
import json
import os
import sys
from importlib import metadata
from typing import List, Optional, Any
from dotenv import load_dotenv, find_dotenv

from yt_tools.core import YouTubeService

# Load .env from current working directory or parent directories
load_dotenv(find_dotenv(usecwd=True))

# If YOUTUBE_API_KEY is not set, try loading from ~/.claude/.env
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
    "docs": """
Show the full documentation.

Usage:
  yt-tools docs
"""
}

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