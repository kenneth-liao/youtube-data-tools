import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from yt_tools.analytics import (
    AnalyticsInputError,
    AnalyticsQuery,
    normalize_channel,
    parse_date,
    query_channel_analytics,
)
from yt_tools.video_metadata import get_video_metadata


CHANNEL_METRICS = (
    "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
    "subscribersGained,subscribersLost"
)
VIDEO_METRICS = (
    "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage"
)


def pacific_today() -> date:
    """Return today's date in YouTube's Pacific-time reporting calendar."""
    return datetime.now(ZoneInfo("America/Los_Angeles")).date()


def resolve_snapshot_range(
    start_date: str | None,
    end_date: str | None,
) -> tuple[str, str]:
    if (start_date is None) != (end_date is None):
        raise AnalyticsInputError(
            "snapshot start date and end date must be provided together."
        )
    if start_date is not None and end_date is not None:
        start = parse_date(start_date, "start date")
        end = parse_date(end_date, "end date")
        if start > end:
            raise AnalyticsInputError("start date must not be after end date.")
        return start_date, end_date
    end = pacific_today() - timedelta(days=1)
    start = end - timedelta(days=27)
    return start.isoformat(), end.isoformat()


def validate_snapshot_target(channel: str, video: str | None) -> str:
    normalized_channel = normalize_channel(channel)
    if video is not None and not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        raise AnalyticsInputError("video must be a YouTube video ID.")
    return normalized_channel


def preceding_period_range(start_date: str, end_date: str) -> tuple[str, str]:
    current_start = date.fromisoformat(start_date)
    current_end = date.fromisoformat(end_date)
    comparison_end = current_start - timedelta(days=1)
    comparison_start = comparison_end - (current_end - current_start)
    return comparison_start.isoformat(), comparison_end.isoformat()


def calculate_changes(
    current_values: dict | None,
    comparison_values: dict | None,
    comparison_columns: list[dict],
) -> dict:
    changes = {}
    comparison_metrics = {
        column["name"]
        for column in comparison_columns
        if column.get("columnType") == "METRIC"
    }
    if current_values is None:
        return changes
    for metric, current_value in current_values.items():
        if metric not in comparison_metrics:
            continue
        baseline = (
            comparison_values.get(metric)
            if comparison_values is not None
            else None
        )
        absolute = (
            current_value - baseline
            if current_value is not None and baseline is not None
            else None
        )
        changes[metric] = {
            "absolute": absolute,
            "percentage": (
                absolute / baseline * 100
                if absolute is not None and baseline != 0
                else None
            ),
        }
    return changes


def create_analytics_snapshot(
    api,
    *,
    channel: str,
    start_date: str,
    end_date: str,
    video: str | None = None,
    data_api=None,
    comparison_enabled: bool = True,
) -> dict:
    """Retrieve aggregate and daily values for a predefined performance view."""
    metrics = VIDEO_METRICS if video else CHANNEL_METRICS
    filters = f"video=={video}" if video else None
    period = query_channel_analytics(api, AnalyticsQuery(
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        filters=filters,
    ))
    daily = query_channel_analytics(api, AnalyticsQuery(
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        dimensions="day",
        filters=filters,
        sort="day",
    ))
    target = {"channel": channel}
    if video:
        target.update({
            "videoId": video,
            "videoMetadata": get_video_metadata(data_api, [video])[video],
        })
    current_values = period["rows"][0] if period["rows"] else None
    result = {
        "target": target,
        "requestedRange": period["requestedRange"],
        "returnedRange": daily["returnedRange"],
        "period": {
            "columns": period["columns"],
            "values": current_values,
        },
        "daily": {
            "columns": daily["columns"],
            "rows": daily["rows"],
        },
    }
    if not comparison_enabled:
        return result

    comparison_start, comparison_end = preceding_period_range(start_date, end_date)
    comparison_period = query_channel_analytics(api, AnalyticsQuery(
        channel=channel,
        start_date=comparison_start,
        end_date=comparison_end,
        metrics=metrics,
        filters=filters,
    ))
    comparison_daily = query_channel_analytics(api, AnalyticsQuery(
        channel=channel,
        start_date=comparison_start,
        end_date=comparison_end,
        metrics=metrics,
        dimensions="day",
        filters=filters,
        sort="day",
    ))
    comparison_values = (
        comparison_period["rows"][0] if comparison_period["rows"] else None
    )
    changes = calculate_changes(
        current_values,
        comparison_values,
        comparison_period["columns"],
    )
    result["comparison"] = {
        "requestedRange": comparison_period["requestedRange"],
        "returnedRange": comparison_daily["returnedRange"],
        "period": {
            "columns": comparison_period["columns"],
            "values": comparison_values,
        },
        "daily": {
            "columns": comparison_daily["columns"],
            "rows": comparison_daily["rows"],
        },
    }
    result["changes"] = changes
    return result
