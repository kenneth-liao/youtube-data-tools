import json
import unittest
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from yt_tools.analytics import (
    AnalyticsInputError,
    AnalyticsQuery,
    AnalyticsQueryError,
    build_analytics_api,
    query_channel_analytics,
)


class TestChannelAnalyticsQuery(unittest.TestCase):
    def test_api_client_uses_authorized_youtube_analytics_v2(self):
        credentials = MagicMock()
        api = MagicMock()

        with patch("yt_tools.analytics.build", return_value=api) as build:
            result = build_analytics_api(credentials)

        self.assertIs(result, api)
        build.assert_called_once_with(
            "youtubeAnalytics",
            "v2",
            credentials=credentials,
            cache_discovery=False,
        )

    def test_success_returns_ordered_columns_and_named_rows(self):
        api = MagicMock()
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [["2026-08-01", 12], ["2026-08-02", 8]],
        }
        query = AnalyticsQuery(
            channel="MINE",
            start_date="2026-08-01",
            end_date="2026-08-02",
            metrics="views",
            dimensions="day",
        )

        result = query_channel_analytics(api, query)

        api.reports.return_value.query.assert_called_once_with(
            ids="channel==MINE",
            startDate="2026-08-01",
            endDate="2026-08-02",
            metrics="views",
            dimensions="day",
        )
        self.assertEqual(result["requestedRange"], {
            "startDate": "2026-08-01",
            "endDate": "2026-08-02",
        })
        self.assertEqual(result["returnedRange"], {
            "startDate": "2026-08-01",
            "endDate": "2026-08-02",
        })
        self.assertEqual(result["columns"], api.reports.return_value.query.return_value.execute.return_value["columnHeaders"])
        self.assertEqual(result["rows"], [
            {"day": "2026-08-01", "views": 12},
            {"day": "2026-08-02", "views": 8},
        ])

    def test_explicit_channel_and_optional_parameters_pass_through_unchanged(self):
        api = MagicMock()
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [],
            "rows": [],
        }
        query = AnalyticsQuery(
            channel="UCabcdefghijklmnopqrstuv",
            start_date="2026-07-01",
            end_date="2026-07-31",
            metrics="newMetric,revenue",
            dimensions="newDimension",
            filters="newFilter==value;country==US",
            sort="-newMetric",
            max_results=25,
            start_index=26,
            currency="USD",
        )

        query_channel_analytics(api, query)

        api.reports.return_value.query.assert_called_once_with(
            ids="channel==UCabcdefghijklmnopqrstuv",
            startDate="2026-07-01",
            endDate="2026-07-31",
            metrics="newMetric,revenue",
            dimensions="newDimension",
            filters="newFilter==value;country==US",
            sort="-newMetric",
            maxResults=25,
            startIndex=26,
            currency="USD",
        )

    def test_malformed_local_input_is_rejected_before_an_api_request(self):
        api = MagicMock()
        invalid_inputs = [
            {"start_date": "20260801"},
            {"start_date": "2026-08-32"},
            {"start_date": "2026-08-03", "end_date": "2026-08-02"},
            {"metrics": ""},
            {"metrics": "views,,likes"},
            {"channel": "not-a-channel"},
            {"max_results": 0},
            {"start_index": 0},
            {"dimensions": "day,"},
            {"filters": " "},
            {"sort": "-views,"},
            {"currency": ""},
        ]

        for overrides in invalid_inputs:
            values = {
                "channel": "MINE",
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "metrics": "views",
                **overrides,
            }
            with self.subTest(overrides=overrides), self.assertRaises(AnalyticsInputError):
                query_channel_analytics(api, AnalyticsQuery(**values))

        api.reports.assert_not_called()

    def test_successful_empty_response_stays_explicitly_empty(self):
        api = MagicMock()
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ]
        }

        result = query_channel_analytics(api, AnalyticsQuery(
            channel="channel==MINE",
            start_date="2026-08-01",
            end_date="2026-08-02",
            metrics="views",
        ))

        self.assertEqual(result["rows"], [])
        self.assertIsNone(result["returnedRange"])
        self.assertNotIn("views", result)

    def test_google_request_error_preserves_actionable_details(self):
        api = MagicMock()
        response = MagicMock(status=400, reason="Bad Request")
        content = json.dumps({
            "error": {
                "message": "The query is not supported.",
                "errors": [{
                    "reason": "invalidFilters",
                    "location": "filters",
                    "message": "The views filter is incompatible with day.",
                }],
            }
        }).encode()
        api.reports.return_value.query.return_value.execute.side_effect = HttpError(
            response,
            content,
        )

        with self.assertRaises(AnalyticsQueryError) as raised:
            query_channel_analytics(api, AnalyticsQuery(
                channel="MINE",
                start_date="2026-08-01",
                end_date="2026-08-02",
                metrics="views",
                filters="views==1",
            ))

        message = str(raised.exception)
        self.assertIn("400", message)
        self.assertIn("The query is not supported.", message)
        self.assertIn("invalidFilters", message)
        self.assertIn("filters", message)
        self.assertIn("The views filter is incompatible with day.", message)

    def test_transport_failure_is_actionable(self):
        api = MagicMock()
        api.reports.return_value.query.return_value.execute.side_effect = OSError(
            "connection reset"
        )

        with self.assertRaisesRegex(
            AnalyticsQueryError,
            "request failed.*connection reset",
        ):
            query_channel_analytics(api, AnalyticsQuery(
                channel="MINE",
                start_date="2026-08-01",
                end_date="2026-08-02",
                metrics="views",
            ))


if __name__ == "__main__":
    unittest.main()
