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


def get_video_metadata(api, video_ids: list[str]) -> dict[str, dict]:
    """Return current authorized Data API metadata keyed by video ID."""
    unique_ids = list(dict.fromkeys(video_ids))
    videos = {}
    try:
        for start in range(0, len(unique_ids), 50):
            response = api.videos().list(
                part="snippet,contentDetails,status",
                id=",".join(unique_ids[start:start + 50]),
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

    metadata = {}
    for video_id in unique_ids:
        item = videos.get(video_id)
        if item:
            metadata[video_id] = {
                "availability": "available",
                **{
                    name: item[name]
                    for name in ("snippet", "contentDetails", "status")
                    if name in item
                },
            }
        else:
            metadata[video_id] = {"availability": "unavailable"}
    return metadata


def enrich_video_rows(api, result: dict) -> dict:
    """Add current Data API metadata to analytics rows containing video IDs."""
    metadata = get_video_metadata(api, [row["video"] for row in result["rows"]])
    enriched_rows = [
        {**row, "videoMetadata": metadata[row["video"]]}
        for row in result["rows"]
    ]
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
