import os
import re
import tempfile
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_tools.google_api import format_http_error


class ReportingError(Exception):
    """An actionable YouTube Reporting API failure."""


class ReportingDiscoveryError(ReportingError):
    """An actionable failure while discovering available report types."""


class ReportingJobError(ReportingError):
    """An actionable failure while managing asynchronous reporting jobs."""


class ReportingDownloadError(ReportingError):
    """An actionable failure while downloading one reporting file."""


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


def suggested_reporting_filename(report: dict) -> str:
    """Return a CSV filename that keeps stable report and backfill identity."""
    components = [report.get("jobId", "job"), report["id"]]
    if report.get("createTime"):
        components.append(re.sub(r"[^A-Za-z0-9]", "", report["createTime"]))
    safe_components = [
        re.sub(r"[^A-Za-z0-9._-]+", "_", str(component)).strip("._-")
        for component in components
    ]
    return "__".join(safe_components) + ".csv"


def download_reporting_job_report(
    api,
    authorized_transport,
    job_id: str,
    report_id: str,
    destination: str | Path,
    *,
    replace: bool = False,
) -> dict:
    """Stream one selected reporting file to an explicit local destination."""
    destination = Path(destination)
    if not destination.parent.is_dir():
        raise ReportingDownloadError(
            f"Destination parent does not exist: {destination.parent}"
        )
    if destination.is_dir():
        raise ReportingDownloadError(
            f"Destination must be a file path: {destination}"
        )
    if destination.exists() and not replace:
        raise ReportingDownloadError(
            f"Destination already exists: {destination}. Use --replace to replace it."
        )
    report = _execute_job_request(
        lambda: api.jobs().reports().get(jobId=job_id, reportId=report_id)
    )
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".part",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            with authorized_transport.get(report["downloadUrl"], stream=True) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
        if replace:
            os.replace(temporary, destination)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise ReportingDownloadError(
                    f"Destination already exists: {destination}. Use --replace to replace it."
                ) from error
            temporary.unlink()
    except ReportingDownloadError:
        raise
    except Exception as error:
        raise ReportingDownloadError(
            f"Reporting file download failed: {error}"
        ) from error
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "jobId": job_id,
        "reportId": report_id,
        "destination": str(destination),
        "status": "downloaded",
    }


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
        reports.extend(
            {
                **report,
                "suggestedFilename": suggested_reporting_filename(report),
            }
            for report in response.get("reports", [])
        )
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


def retrieve_thumbnail_reach_reports(api) -> dict:
    """Establish reach reporting and expose every generated file without waiting."""
    report_type = next(
        (
            report_type
            for report_type in list_report_types(api)["reportTypes"]
            if report_type["name"].casefold() == "reach basic"
            and "deprecateTime" not in report_type
        ),
        None,
    )
    if report_type is None:
        raise ReportingDiscoveryError(
            "No current non-deprecated Reach Basic report type is available "
            "for the authorized channel."
        )
    jobs = list_reporting_jobs(api)["jobs"]
    job = next(
        (job for job in jobs if job["reportTypeId"] == report_type["id"]),
        None,
    )
    disposition = "reused"
    if job is None:
        job = create_reporting_job(
            api, report_type["id"], "yt-tools thumbnail reach"
        )
        disposition = "created"
    reports = list_reporting_job_reports(api, job["id"])
    result = {
        "state": "available" if reports["reports"] else "pending",
        "reportType": report_type,
        "job": job,
        "jobDisposition": disposition,
        "fields": [
            {
                "name": "video_thumbnail_impressions",
                "meaning": "Video thumbnail impressions",
            },
            {
                "name": "video_thumbnail_impressions_ctr",
                "meaning": "Video thumbnail impression click-through rate",
            },
        ],
        "reports": reports["reports"],
    }
    if not reports["reports"]:
        result["message"] = (
            "Reach files are not yet available. The reporting job remains pending."
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
