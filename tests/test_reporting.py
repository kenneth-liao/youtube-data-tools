import json
import unittest
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from yt_tools.reporting import (
    ReportingDiscoveryError,
    build_reporting_api,
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


if __name__ == "__main__":
    unittest.main()
