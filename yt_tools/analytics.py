import re
from dataclasses import dataclass
from datetime import date

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


class AnalyticsInputError(ValueError):
    """A malformed analytics query that can be corrected locally."""


class AnalyticsQueryError(Exception):
    """An actionable failure returned by the YouTube Analytics API."""


def _parse_date(value: str, field: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise AnalyticsInputError(f"{field} must use YYYY-MM-DD format.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise AnalyticsInputError(f"{field} must be a valid calendar date.") from error


def _validate_text(value: str | None, field: str, *, required: bool = False) -> None:
    if value is None:
        if required:
            raise AnalyticsInputError(f"{field} is required.")
        return
    if not isinstance(value, str) or not value.strip():
        raise AnalyticsInputError(f"{field} cannot be empty.")


def _validate_list(value: str | None, field: str, *, required: bool = False) -> None:
    _validate_text(value, field, required=required)
    if value is not None and any(not item.strip() for item in value.split(",")):
        raise AnalyticsInputError(f"{field} contains an empty name.")


@dataclass(frozen=True)
class AnalyticsQuery:
    channel: str
    start_date: str
    end_date: str
    metrics: str
    dimensions: str | None = None
    filters: str | None = None
    sort: str | None = None
    max_results: int | None = None
    start_index: int | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        start = _parse_date(self.start_date, "start date")
        end = _parse_date(self.end_date, "end date")
        if start > end:
            raise AnalyticsInputError("start date must not be after end date.")

        channel = (
            self.channel.removeprefix("channel==")
            if isinstance(self.channel, str)
            else ""
        )
        if channel != "MINE" and not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel):
            raise AnalyticsInputError("channel must be MINE or a YouTube channel ID.")
        object.__setattr__(self, "channel", f"channel=={channel}")

        _validate_list(self.metrics, "metrics", required=True)
        _validate_list(self.dimensions, "dimensions")
        _validate_list(self.sort, "sort")
        _validate_text(self.filters, "filters")
        _validate_text(self.currency, "currency")
        for value, field in (
            (self.max_results, "max results"),
            (self.start_index, "start index"),
        ):
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 1
            ):
                raise AnalyticsInputError(f"{field} must be a positive integer.")


def build_analytics_api(credentials):
    """Build an authorized YouTube Analytics API v2 client."""
    try:
        return build(
            "youtubeAnalytics",
            "v2",
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as error:
        raise AnalyticsQueryError(
            f"Failed to initialize the YouTube Analytics API client: {error}"
        ) from error


def query_channel_analytics(api, query: AnalyticsQuery) -> dict:
    parameters = {
        "ids": query.channel,
        "startDate": query.start_date,
        "endDate": query.end_date,
        "metrics": query.metrics,
    }
    optional_parameters = {
        "dimensions": query.dimensions,
        "filters": query.filters,
        "sort": query.sort,
        "maxResults": query.max_results,
        "startIndex": query.start_index,
        "currency": query.currency,
    }
    parameters.update(
        {name: value for name, value in optional_parameters.items() if value is not None}
    )

    try:
        response = api.reports().query(**parameters).execute()
    except HttpError as error:
        raise AnalyticsQueryError(
            format_http_error(error, "YouTube Analytics API")
        ) from error
    except Exception as error:
        raise AnalyticsQueryError(
            f"YouTube Analytics API request failed: {error}"
        ) from error
    columns = response.get("columnHeaders", [])
    names = [column["name"] for column in columns]
    rows = [
        dict(zip(names, values, strict=True))
        for values in response.get("rows", [])
    ]
    returned_days = [row["day"] for row in rows if "day" in row]
    return {
        "requestedRange": {
            "startDate": query.start_date,
            "endDate": query.end_date,
        },
        "returnedRange": (
            {"startDate": min(returned_days), "endDate": max(returned_days)}
            if returned_days
            else None
        ),
        "columns": columns,
        "rows": rows,
    }
