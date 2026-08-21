from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


class ReportingError(Exception):
    """An actionable YouTube Reporting API failure."""


class ReportingDiscoveryError(ReportingError):
    """An actionable failure while discovering available report types."""


class ReportingJobError(ReportingError):
    """An actionable failure while managing asynchronous reporting jobs."""


def _execute_job_request(operation):
    try:
        return operation().execute()
    except HttpError as error:
        raise ReportingJobError(
            format_http_error(error, "YouTube Reporting API")
        ) from error
    except Exception as error:
        raise ReportingJobError(
            f"YouTube Reporting API request failed: {error}"
        ) from error


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


def create_reporting_job(api, report_type_id: str, name: str) -> dict:
    """Create an asynchronous reporting job without waiting for reports."""
    return _execute_job_request(
        lambda: api.jobs().create(body={
            "reportTypeId": report_type_id,
            "name": name,
        })
    )


def delete_reporting_job(api, job_id: str) -> dict:
    """Delete one asynchronous reporting job by its upstream identity."""
    _execute_job_request(lambda: api.jobs().delete(jobId=job_id))
    return {"id": job_id, "status": "deleted"}


def list_reporting_jobs(api) -> dict:
    """List asynchronous reporting jobs and their upstream lifecycle metadata."""
    jobs = []
    page_token = None
    while True:
        parameters = {"pageToken": page_token} if page_token else {}
        response = _execute_job_request(
            lambda: api.jobs().list(**parameters)
        )
        jobs.extend(response.get("jobs", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return {"jobs": jobs}


def list_reporting_job_reports(api, job_id: str) -> dict:
    """List generated reporting files for one reporting job."""
    reports = []
    page_token = None
    while True:
        parameters = {"jobId": job_id}
        if page_token:
            parameters["pageToken"] = page_token
        response = _execute_job_request(
            lambda: api.jobs().reports().list(**parameters)
        )
        reports.extend(response.get("reports", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            result = {
                "availability": "available" if reports else "empty",
                "reports": reports,
            }
            if not reports:
                result["message"] = (
                    "No generated files are available for reporting job "
                    f"{job_id}."
                )
            return result


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
