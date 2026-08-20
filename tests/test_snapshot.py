import json
import sys
import unittest
from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

from yt_tools import cli


class TestAnalyticsSnapshotCLI(unittest.TestCase):
    def setUp(self):
        self.stdout, sys.stdout = sys.stdout, StringIO()
        self.stderr, sys.stderr = sys.stderr, StringIO()

    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    @patch("yt_tools.snapshot.pacific_today", return_value=date(2026, 8, 20))
    def test_channel_snapshot_defaults_to_28_completed_pacific_days_and_uses_api_aggregates(
        self,
        pacific_today,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        execute = api.reports.return_value.query.return_value.execute
        execute.side_effect = [
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                    {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                ],
                "rows": [[50, 62.5]],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                    {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                ],
                "rows": [["2026-07-25", 20, 50.0], ["2026-08-17", 30, 75.0]],
            },
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                    {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                ],
                "rows": [[40, 50.0]],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                    {"name": "averageViewPercentage", "columnType": "METRIC", "dataType": "FLOAT"},
                ],
                "rows": [["2026-06-25", 40, 50.0]],
            },
        ]

        result = cli.main(["analytics", "snapshot", "--channel", "MINE"])

        self.assertEqual(result, 0)
        self.assertEqual(api.reports.return_value.query.call_count, 4)
        aggregate_call, daily_call, comparison_aggregate_call, comparison_daily_call = (
            api.reports.return_value.query.call_args_list
        )
        self.assertEqual(aggregate_call.kwargs["startDate"], "2026-07-23")
        self.assertEqual(aggregate_call.kwargs["endDate"], "2026-08-19")
        self.assertNotIn("dimensions", aggregate_call.kwargs)
        self.assertIn("subscribersGained", aggregate_call.kwargs["metrics"])
        self.assertIn("subscribersLost", aggregate_call.kwargs["metrics"])
        self.assertEqual(daily_call.kwargs["dimensions"], "day")
        self.assertEqual(daily_call.kwargs["sort"], "day")
        for call in (comparison_aggregate_call, comparison_daily_call):
            self.assertEqual(call.kwargs["startDate"], "2026-06-25")
            self.assertEqual(call.kwargs["endDate"], "2026-07-22")
        output = json.loads(sys.stdout.getvalue())
        self.assertEqual(output["requestedRange"], {
            "startDate": "2026-07-23",
            "endDate": "2026-08-19",
        })
        self.assertEqual(output["returnedRange"], {
            "startDate": "2026-07-25",
            "endDate": "2026-08-17",
        })
        self.assertEqual(output["period"]["values"], {
            "views": 50,
            "averageViewPercentage": 62.5,
        })
        self.assertEqual(output["daily"]["rows"], [
            {"day": "2026-07-25", "views": 20, "averageViewPercentage": 50.0},
            {"day": "2026-08-17", "views": 30, "averageViewPercentage": 75.0},
        ])
        self.assertEqual(output["comparison"]["requestedRange"], {
            "startDate": "2026-06-25",
            "endDate": "2026-07-22",
        })
        self.assertEqual(output["comparison"]["returnedRange"], {
            "startDate": "2026-06-25",
            "endDate": "2026-06-25",
        })
        self.assertEqual(output["comparison"]["period"]["values"], {
            "views": 40,
            "averageViewPercentage": 50.0,
        })
        self.assertEqual(output["changes"], {
            "views": {"absolute": 10, "percentage": 25.0},
            "averageViewPercentage": {"absolute": 12.5, "percentage": 25.0},
        })

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_no_comparison_skips_preceding_period_requests(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.side_effect = [
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [[12]],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [["2026-08-01", 12]],
            },
        ]

        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-01",
            "--no-comparison",
        ])

        self.assertEqual(result, 0)
        self.assertEqual(api.reports.return_value.query.call_count, 2)
        output = json.loads(sys.stdout.getvalue())
        self.assertNotIn("comparison", output)
        self.assertNotIn("changes", output)

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_zero_or_absent_baselines_have_undefined_percentage_without_hiding_missing_rows(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        aggregate_columns = [
            {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            {"name": "estimatedMinutesWatched", "columnType": "METRIC", "dataType": "INTEGER"},
        ]
        daily_columns = [
            {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
            *aggregate_columns,
        ]
        api.reports.return_value.query.return_value.execute.side_effect = [
            {"columnHeaders": aggregate_columns, "rows": [[0, 10]]},
            {"columnHeaders": daily_columns, "rows": [["2026-08-01", 0, 10]]},
            {"columnHeaders": aggregate_columns, "rows": [[0, None]]},
            {"columnHeaders": daily_columns, "rows": []},
        ]

        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-01",
        ])

        self.assertEqual(result, 0)
        output = json.loads(sys.stdout.getvalue())
        self.assertEqual(output["period"]["values"]["views"], 0)
        self.assertEqual(output["daily"]["rows"][0]["views"], 0)
        self.assertIsNone(output["comparison"]["returnedRange"])
        self.assertEqual(output["comparison"]["daily"]["rows"], [])
        self.assertEqual(output["changes"], {
            "views": {"absolute": 0, "percentage": None},
            "estimatedMinutesWatched": {"absolute": None, "percentage": None},
        })

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_missing_comparison_period_has_explicit_undefined_changes(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        aggregate_columns = [
            {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
        ]
        daily_columns = [
            {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
            *aggregate_columns,
        ]
        api.reports.return_value.query.return_value.execute.side_effect = [
            {"columnHeaders": aggregate_columns, "rows": [[10]]},
            {"columnHeaders": daily_columns, "rows": [["2026-08-01", 10]]},
            {"columnHeaders": aggregate_columns, "rows": []},
            {"columnHeaders": daily_columns, "rows": []},
        ]

        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-01",
        ])

        self.assertEqual(result, 0)
        output = json.loads(sys.stdout.getvalue())
        self.assertIsNone(output["comparison"]["period"]["values"])
        self.assertEqual(output["changes"], {
            "views": {"absolute": None, "percentage": None},
        })

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_snapshot_rejects_partial_explicit_range_before_authorization(
        self,
        load_credentials,
        build_api,
    ):
        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
        ])

        self.assertEqual(result, 1)
        self.assertIn("must be provided together", sys.stderr.getvalue())
        load_credentials.assert_not_called()
        build_api.assert_not_called()

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_snapshot_rejects_invalid_dates_before_authorization(
        self,
        load_credentials,
        build_api,
    ):
        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "not-a-date",
            "--end-date", "2026-08-01",
        ])

        self.assertEqual(result, 1)
        self.assertIn("start date", sys.stderr.getvalue())
        load_credentials.assert_not_called()
        build_api.assert_not_called()

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_snapshot_rejects_an_invalid_video_id_before_authorization(
        self,
        load_credentials,
        build_api,
    ):
        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--video", "not a video id",
        ])

        self.assertEqual(result, 1)
        self.assertIn("video", sys.stderr.getvalue())
        load_credentials.assert_not_called()
        build_api.assert_not_called()

    @patch("yt_tools.cli.build_data_api")
    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_video_snapshot_omits_subscriber_metrics_and_enriches_the_preserved_video_id(
        self,
        load_credentials,
        build_analytics_api,
        build_data_api,
    ):
        analytics_api = MagicMock()
        build_analytics_api.return_value = analytics_api
        analytics_api.reports.return_value.query.return_value.execute.side_effect = [
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [[12]],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [["2026-08-01", 12]],
            },
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [[8]],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [["2026-07-31", 8]],
            },
        ]
        data_api = MagicMock()
        build_data_api.return_value = data_api
        data_api.videos.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "abcdefghijk",
                "snippet": {"title": "Current title"},
                "contentDetails": {"duration": "PT2M"},
                "status": {"privacyStatus": "unlisted"},
            }]
        }

        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--video", "abcdefghijk",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-01",
        ])

        self.assertEqual(result, 0)
        calls = analytics_api.reports.return_value.query.call_args_list
        for call in calls[:2]:
            self.assertEqual(call.kwargs["startDate"], "2026-08-01")
            self.assertEqual(call.kwargs["endDate"], "2026-08-01")
        for call in calls[2:]:
            self.assertEqual(call.kwargs["startDate"], "2026-07-31")
            self.assertEqual(call.kwargs["endDate"], "2026-07-31")
        for call in calls:
            self.assertEqual(call.kwargs["filters"], "video==abcdefghijk")
            self.assertNotIn("subscribersGained", call.kwargs["metrics"])
            self.assertNotIn("subscribersLost", call.kwargs["metrics"])
        output = json.loads(sys.stdout.getvalue())
        self.assertEqual(output["target"], {
            "channel": "channel==MINE",
            "videoId": "abcdefghijk",
            "videoMetadata": {
                "availability": "available",
                "snippet": {"title": "Current title"},
                "contentDetails": {"duration": "PT2M"},
                "status": {"privacyStatus": "unlisted"},
            },
        })

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_empty_snapshot_keeps_period_and_returned_range_null_without_fabricated_values(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.side_effect = [
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [],
            },
            {
                "columnHeaders": [
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [],
            },
            {
                "columnHeaders": [
                    {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                    {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                ],
                "rows": [],
            },
        ]

        result = cli.main([
            "analytics", "snapshot",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
        ])

        self.assertEqual(result, 0)
        output = json.loads(sys.stdout.getvalue())
        self.assertIsNone(output["returnedRange"])
        self.assertIsNone(output["period"]["values"])
        self.assertEqual(output["daily"]["rows"], [])
        self.assertNotIn("analysis", output)


if __name__ == "__main__":
    unittest.main()
