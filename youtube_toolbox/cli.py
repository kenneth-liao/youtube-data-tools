import argparse
import json
import os
import sys
from importlib import metadata
from typing import List, Optional, Any
from dotenv import load_dotenv, find_dotenv

from youtube_toolbox.core import YouTubeService

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
        return metadata.version("youtube-data-api")
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
    """Display CLI documentation."""
    docs = """
YouTube Toolbox CLI Reference

Usage: youtube-toolbox <command> [arguments]

Commands:
  search       Search for videos
  details      Get video details
  channel      Get channel details
  transcript   Get video transcript
  comments     Get video comments
  related      Get related videos
  trending     Get trending videos
  docs         Show this documentation

Environment Variables:
  YOUTUBE_API_KEY  Required. Your Google Data API key.

Examples:
  youtube-toolbox search "python tutorials" --max-results 5
  youtube-toolbox details <video_id>
  youtube-toolbox transcript <video_id> --language en
    """
    print(docs)
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        "youtube-toolbox",
        description="YouTube Toolbox CLI (MCP Compatible)",
        epilog="Run 'youtube-toolbox docs' for full documentation"
    )
    p.add_argument(
        "-v", "--version",
        action="version",
        version=f"youtube-toolbox {get_version()}"
    )
    sub = p.add_subparsers(dest="cmd", required=False)

    # Search
    s = sub.add_parser("search", help="Search for YouTube videos")
    s.add_argument("query", help="Search query")
    s.add_argument("--max-results", type=int, default=10, help="Max results (default: 10)")
    s.add_argument("--channel-id", help="Filter by channel ID")
    s.add_argument("--order", choices=['date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'], help="Sort order")
    s.add_argument("--duration", choices=['any', 'long', 'medium', 'short'], help="Filter by duration")
    s.add_argument("--json", action="store_true", help="Output JSON")
    s.set_defaults(func=cmd_search)

    # Details
    d = sub.add_parser("details", help="Get video details")
    d.add_argument("video_id", help="YouTube Video ID or URL")
    d.add_argument("--json", action="store_true", help="Output JSON")
    d.set_defaults(func=cmd_details)

    # Channel
    c = sub.add_parser("channel", help="Get channel details")
    c.add_argument("channel_id", help="YouTube Channel ID or URL")
    c.add_argument("--json", action="store_true", help="Output JSON")
    c.set_defaults(func=cmd_channel)

    # Transcript
    t = sub.add_parser("transcript", help="Get video transcript")
    t.add_argument("video_id", help="YouTube Video ID or URL")
    t.add_argument("--language", help="Language code (e.g., 'en', 'ko')")
    t.add_argument("--json", action="store_true", help="Output JSON")
    t.set_defaults(func=cmd_transcript)

    # Comments
    cm = sub.add_parser("comments", help="Get video comments")
    cm.add_argument("video_id", help="YouTube Video ID or URL")
    cm.add_argument("--max-results", type=int, default=20, help="Max comments (default: 20)")
    cm.add_argument("--order", choices=['time', 'relevance'], default='relevance', help="Order by")
    cm.add_argument("--replies", action="store_true", help="Include replies")
    cm.add_argument("--json", action="store_true", help="Output JSON")
    cm.set_defaults(func=cmd_comments)

    # Related
    r = sub.add_parser("related", help="Get related videos")
    r.add_argument("video_id", help="YouTube Video ID or URL")
    r.add_argument("--max-results", type=int, default=10, help="Max results")
    r.add_argument("--json", action="store_true", help="Output JSON")
    r.set_defaults(func=cmd_related)

    # Trending
    tr = sub.add_parser("trending", help="Get trending videos")
    tr.add_argument("--region", default="US", help="Region code (default: US)")
    tr.add_argument("--max-results", type=int, default=10, help="Max results")
    tr.add_argument("--json", action="store_true", help="Output JSON")
    tr.set_defaults(func=cmd_trending)

    # Docs
    doc = sub.add_parser("docs", help="Display full documentation")
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
