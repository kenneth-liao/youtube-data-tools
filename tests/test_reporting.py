import json
import unittest
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from yt_tools.reporting import (
    ReportingDiscoveryError,
    ReportingJobError,
    build_reporting_api,
    create_reporting_job,
    delete_reporting_job,
    list_reporting_jobs,
    list_report_types,
)


class TestReportTypeDiscovery(unittest.TestCase):
    def test_api_client_uses_authorized_youtube_reporting_v1(self):
        credentials = MagicMock()
        api = MagicMock()

        with patch("yt_tools.reporting.build", return_value=api) as build:
            result = build_reporting_api(credentials)

        self.assertIs(result, api)
        build.assert_called_once_with(
            "youtubereporting",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    def test_api_client_initialization_failure_is_actionable(self):
        with patch("yt_tools.reporting.build", side_effect=OSError("discovery unavailable")):
            with self.assertRaisesRegex(
                ReportingDiscoveryError,
                "Failed to initialize the YouTube Reporting API client.*discovery unavailable",
            ):
                build_reporting_api(MagicMock())

    def test_available_report_types_preserve_upstream_fields_and_identify_reach(self):
        api = MagicMock()
        api.reportTypes.return_value.list.return_value.execute.return_value = {
            "reportTypes": [
                {
                    "id": "channel_reach_basic_a99",
                    "name": "Reach Basic",
                    "deprecateTime": "2027-01-01T00:00:00Z",
                    "systemManaged": False,
                },
                {
                    "id": "channel_basic_a3",
                    "name": "User activity",
                },
            ]
        }

        result = list_report_types(api)

        self.assertEqual(result, {
            "availability": "available",
            "reportTypes": [
                {
                    "id": "channel_reach_basic_a99",
                    "name": "Reach Basic",
                    "deprecateTime": "2027-01-01T00:00:00Z",
                    "systemManaged": False,
                    "isReachReport": True,
                },
                {
                    "id": "channel_basic_a3",
                    "name": "User activity",
                    "systemManaged": False,
                    "isReachReport": False,
                },
            ],
        })

    def test_empty_availability_is_an_explicit_successful_outcome(self):
        api = MagicMock()
        api.reportTypes.return_value.list.return_value.execute.return_value = {}

        result = list_report_types(api)

        self.assertEqual(result, {
            "availability": "empty",
            "reportTypes": [],
            "message": "No report types are available for the authorized channel.",
        })

    def test_api_failure_is_actionable_and_not_empty_availability(self):
        api = MagicMock()
        api.reportTypes.return_value.list.return_value.execute.side_effect = HttpError(
            MagicMock(status=403, reason="Forbidden"),
            json.dumps({
                "error": {
                    "message": "YouTube Reporting API has not been used.",
                    "errors": [{"reason": "accessNotConfigured"}],
                }
            }).encode(),
        )

        with self.assertRaises(ReportingDiscoveryError) as raised:
            list_report_types(api)

        message = str(raised.exception)
        self.assertIn("YouTube Reporting API request failed (403)", message)
        self.assertIn("has not been used", message)
        self.assertIn("accessNotConfigured", message)

    def test_transport_failure_is_actionable(self):
        api = MagicMock()
        api.reportTypes.return_value.list.return_value.execute.side_effect = OSError(
            "connection reset"
        )

        with self.assertRaisesRegex(
            ReportingDiscoveryError,
            "YouTube Reporting API request failed.*connection reset",
        ):
            list_report_types(api)

    def test_all_pages_are_included(self):
        api = MagicMock()
        first_page = MagicMock()
        first_page.execute.return_value = {
            "reportTypes": [{
                "id": "channel_basic_a3",
                "name": "User activity",
                "systemManaged": False,
            }],
            "nextPageToken": "next-page",
        }
        second_page = MagicMock()
        second_page.execute.return_value = {
            "reportTypes": [{
                "id": "channel_reach_combined_a7",
                "name": "Reach Combined",
                "systemManaged": False,
            }]
        }
        api.reportTypes.return_value.list.side_effect = [first_page, second_page]

        result = list_report_types(api)

        self.assertEqual(
            [report_type["id"] for report_type in result["reportTypes"]],
            ["channel_basic_a3", "channel_reach_combined_a7"],
        )
        api.reportTypes.return_value.list.assert_any_call()
        api.reportTypes.return_value.list.assert_any_call(pageToken="next-page")


class TestReportingJobs(unittest.TestCase):
    def test_create_returns_stable_upstream_identity_and_creation_metadata(self):
        api = MagicMock()
        api.jobs.return_value.create.return_value.execute.return_value = {
            "id": "job-123",
            "reportTypeId": "channel_basic_a3",
            "name": "Daily channel export",
            "createTime": "2026-08-21T10:00:00Z",
        }

        result = create_reporting_job(
            api,
            "channel_basic_a3",
            "Daily channel export",
        )

        self.assertEqual(result, {
            "id": "job-123",
            "reportTypeId": "channel_basic_a3",
            "name": "Daily channel export",
            "createTime": "2026-08-21T10:00:00Z",
        })
        api.jobs.return_value.create.assert_called_once_with(body={
            "reportTypeId": "channel_basic_a3",
            "name": "Daily channel export",
        })

    def test_list_preserves_lifecycle_metadata_across_pages(self):
        api = MagicMock()
        first_page = MagicMock()
        first_page.execute.return_value = {
            "jobs": [{
                "id": "job-1",
                "reportTypeId": "channel_basic_a3",
                "name": "Active job",
                "createTime": "2026-08-20T10:00:00Z",
                "systemManaged": False,
            }],
            "nextPageToken": "next-page",
        }
        second_page = MagicMock()
        second_page.execute.return_value = {
            "jobs": [{
                "id": "job-2",
                "reportTypeId": "channel_reach_basic_a42",
                "name": "Expiring job",
                "createTime": "2026-08-19T10:00:00Z",
                "expireTime": "2026-09-19T10:00:00Z",
                "systemManaged": True,
            }]
        }
        api.jobs.return_value.list.side_effect = [first_page, second_page]

        result = list_reporting_jobs(api)

        self.assertEqual(result, {
            "jobs": [
                {
                    "id": "job-1",
                    "reportTypeId": "channel_basic_a3",
                    "name": "Active job",
                    "createTime": "2026-08-20T10:00:00Z",
                    "systemManaged": False,
                },
                {
                    "id": "job-2",
                    "reportTypeId": "channel_reach_basic_a42",
                    "name": "Expiring job",
                    "createTime": "2026-08-19T10:00:00Z",
                    "expireTime": "2026-09-19T10:00:00Z",
                    "systemManaged": True,
                },
            ]
        })
        api.jobs.return_value.list.assert_any_call()
        api.jobs.return_value.list.assert_any_call(pageToken="next-page")

    def test_delete_returns_explicit_success_for_the_selected_upstream_job(self):
        api = MagicMock()
        api.jobs.return_value.delete.return_value.execute.return_value = None

        result = delete_reporting_job(api, "job-123")

        self.assertEqual(result, {"id": "job-123", "status": "deleted"})
        api.jobs.return_value.delete.assert_called_once_with(jobId="job-123")

    def test_invalid_report_type_returns_an_actionable_upstream_error(self):
        api = MagicMock()
        api.jobs.return_value.create.return_value.execute.side_effect = HttpError(
            MagicMock(status=400, reason="Bad Request"),
            json.dumps({
                "error": {
                    "message": "The report type does not exist.",
                    "errors": [{"reason": "invalidValue", "location": "reportTypeId"}],
                }
            }).encode(),
        )

        with self.assertRaises(ReportingJobError) as raised:
            create_reporting_job(api, "unknown-type", "Invalid job")

        message = str(raised.exception)
        self.assertIn("YouTube Reporting API request failed (400)", message)
        self.assertIn("report type does not exist", message)
        self.assertIn("invalidValue", message)
        self.assertIn("reportTypeId", message)

    def test_delete_distinguishes_absent_and_unauthorized_jobs(self):
        api = MagicMock()
        errors = {
            "missing-job": HttpError(
                MagicMock(status=404, reason="Not Found"),
                json.dumps({"error": {"message": "Job not found."}}).encode(),
            ),
            "private-job": HttpError(
                MagicMock(status=403, reason="Forbidden"),
                json.dumps({"error": {"message": "Job access denied."}}).encode(),
            ),
        }
        api.jobs.return_value.delete.return_value.execute.side_effect = (
            lambda: (_ for _ in ()).throw(errors[current_job[0]])
        )

        for job_id, status, detail in (
            ("missing-job", "404", "not found"),
            ("private-job", "403", "access denied"),
        ):
            with self.subTest(job_id=job_id):
                current_job = [job_id]
                with self.assertRaises(ReportingJobError) as raised:
                    delete_reporting_job(api, job_id)
                message = str(raised.exception)
                self.assertIn(f"request failed ({status})", message)
                self.assertIn(detail, message.lower())


if __name__ == "__main__":
    unittest.main()
