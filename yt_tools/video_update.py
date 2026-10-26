from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


EDITABLE_FIELDS = ("title", "description", "tags")

READ_ONLY_SNIPPET_FIELDS = (
    "publishedAt",
    "channelId",
    "thumbnails",
    "channelTitle",
    "liveBroadcastContent",
    "localized",
)


class VideoUpdateError(Exception):
    """An actionable failure while editing an owned video's metadata."""


def _requested(title, description, tags) -> dict:
    return {
        name: value
        for name, value in (("title", title), ("description", description), ("tags", tags))
        if value is not None
    }


def validate_update_fields(
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Return the requested fields, rejecting invalid input before any API call."""
    requested = _requested(title, description, tags)
    if not requested:
        raise VideoUpdateError(
            "Select at least one field to change: --title, --description, "
            "--description-file, --tags, or --clear-tags."
        )
    if title is not None and not title.strip():
        raise VideoUpdateError("The video title cannot be empty.")
    return requested


def build_snippet_update(
    current: dict,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Return the full writable snippet with only the requested fields replaced.

    videos.update replaces the whole snippet, so omitted writable fields such as
    tags or categoryId would be cleared.
    """
    snippet = {
        name: value
        for name, value in current.items()
        if name not in READ_ONLY_SNIPPET_FIELDS
    }
    snippet.update(_requested(title, description, tags))
    return snippet


def _execute(request):
    try:
        return request.execute()
    except HttpError as error:
        raise VideoUpdateError(format_http_error(error, "YouTube Data API")) from error
    except Exception as error:
        raise VideoUpdateError(f"YouTube Data API request failed: {error}") from error


def _current_value(snippet: dict, field: str):
    return snippet.get(field, []) if field == "tags" else snippet.get(field)


def update_video_metadata(
    api,
    video_id: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    apply: bool = False,
) -> dict:
    """Preview, or with apply save, title/description/tag changes to an owned video."""
    requested = validate_update_fields(title, description, tags)

    items = _execute(api.videos().list(part="snippet", id=video_id)).get("items", [])
    if not items:
        raise VideoUpdateError(
            f"Video {video_id} was not found. Check the video ID."
        )
    current = items[0]["snippet"]

    owned = _execute(api.channels().list(part="id", mine=True)).get("items", [])
    if current.get("channelId") not in {channel["id"] for channel in owned}:
        raise VideoUpdateError(
            f"Video {video_id} is not owned by the authorized channel. "
            "Run yt-tools authorize --write as the channel owner."
        )

    proposed = build_snippet_update(current, title, description, tags)
    changes = {
        field: {"current": _current_value(current, field), "proposed": value}
        for field, value in requested.items()
        if _current_value(current, field) != value
    }
    result = {"videoId": video_id, "applied": False, "changes": changes}
    if apply and changes:
        response = _execute(
            api.videos().update(
                part="snippet", body={"id": video_id, "snippet": proposed}
            )
        )
        saved = response.get("snippet", {})
        result["applied"] = True
        result["saved"] = {
            field: _current_value(saved, field) for field in EDITABLE_FIELDS
        }
    return result
