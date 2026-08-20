from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


class VideoMetadataError(Exception):
    """An actionable failure while enriching analytics video rows."""


def build_data_api(credentials):
    """Build an authorized YouTube Data API v3 client."""
    try:
        return build("youtube", "v3", credentials=credentials, cache_discovery=False)
    except Exception as error:
        raise VideoMetadataError(
            f"Failed to initialize the YouTube Data API client: {error}"
        ) from error


def enrich_video_rows(api, result: dict) -> dict:
    """Add current Data API metadata to analytics rows containing video IDs."""
    video_ids = list(dict.fromkeys(row["video"] for row in result["rows"]))
    videos = {}
    try:
        for start in range(0, len(video_ids), 50):
            response = api.videos().list(
                part="snippet,contentDetails,status",
                id=",".join(video_ids[start:start + 50]),
            ).execute()
            videos.update((item["id"], item) for item in response.get("items", []))
    except HttpError as error:
        raise VideoMetadataError(
            format_http_error(error, "YouTube Data API")
        ) from error
    except Exception as error:
        raise VideoMetadataError(
            f"YouTube Data API request failed: {error}"
        ) from error
    enriched_rows = []
    for row in result["rows"]:
        item = videos.get(row["video"])
        metadata = {"availability": "available"}
        if item:
            metadata.update(
                (name, item[name])
                for name in ("snippet", "contentDetails", "status")
                if name in item
            )
        else:
            metadata = {"availability": "unavailable"}
        enriched_rows.append({**row, "videoMetadata": metadata})
    return {
        **result,
        "columns": [
            *result["columns"],
            {
                "name": "videoMetadata",
                "columnType": "METADATA",
                "dataType": "OBJECT",
            },
        ],
        "rows": enriched_rows,
    }
