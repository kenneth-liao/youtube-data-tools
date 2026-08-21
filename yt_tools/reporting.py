from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


class ReportingDiscoveryError(Exception):
    """An actionable failure while discovering available report types."""


def build_reporting_api(credentials):
    """Build an authorized YouTube Reporting API v1 client."""
    try:
        return build(
            "youtubereporting",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as error:
        raise ReportingDiscoveryError(
            f"Failed to initialize the YouTube Reporting API client: {error}"
        ) from error


def list_report_types(api) -> dict:
    """List reporting types available to the authorized channel."""
    report_types = []
    page_token = None
    while True:
        parameters = {"pageToken": page_token} if page_token else {}
        try:
            response = api.reportTypes().list(**parameters).execute()
        except HttpError as error:
            raise ReportingDiscoveryError(
                format_http_error(error, "YouTube Reporting API")
            ) from error
        except Exception as error:
            raise ReportingDiscoveryError(
                f"YouTube Reporting API request failed: {error}"
            ) from error
        for upstream in response.get("reportTypes", []):
            report_type = {
                "id": upstream["id"],
                "name": upstream["name"],
                "systemManaged": upstream.get("systemManaged", False),
                "isReachReport": "reach" in upstream["name"].casefold().split(),
            }
            if "deprecateTime" in upstream:
                report_type["deprecateTime"] = upstream["deprecateTime"]
            report_types.append(report_type)
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    result = {
        "availability": "available" if report_types else "empty",
        "reportTypes": report_types,
    }
    if not report_types:
        result["message"] = (
            "No report types are available for the authorized channel."
        )
    return result
