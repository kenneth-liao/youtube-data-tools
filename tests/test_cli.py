import argparse
import csv
import json
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from yt_tools import cli
from yt_tools.auth import AuthorizationError
from yt_tools.reporting import ReportingDiscoveryError

class TestCLI(unittest.TestCase):
    def setUp(self):
        # Redirect stdout/stderr to capture output
        self.held, sys.stdout = sys.stdout, StringIO()
        self.held_err, sys.stderr = sys.stderr, StringIO()
        
    def tearDown(self):
        sys.stdout = self.held
        sys.stderr = self.held_err

    @patch('yt_tools.cli._get_service')
    def test_search_command(self, mock_get_service):
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock response
        mock_service.search_videos.return_value = {
            'items': [
                {
                    'id': {'videoId': 'video123'},
                    'snippet': {
                        'title': 'Test Video',
                        'channelTitle': 'Test Channel'
                    }
                }
            ]
        }
        
        # Test arguments
        args = argparse.Namespace(
            query="python",
            max_results=5,
            channel_id=None,
            order=None,
            duration=None,
            json=False
        )
        
        # Execute
        ret = cli.cmd_search(args)
        
        # Verify
        self.assertEqual(ret, 0)
        mock_service.search_videos.assert_called_with("python", 5)
        output = sys.stdout.getvalue()
        self.assertIn("Test Video", output)
        self.assertIn("video123", output)

    @patch('yt_tools.cli._get_service')
    def test_search_command_json(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.search_videos.return_value = {'items': []}
        
        args = argparse.Namespace(
            query="python",
            max_results=5,
            channel_id="channel123",
            order="date",
            duration="short",
            json=True
        )
        
        ret = cli.cmd_search(args)
        
        self.assertEqual(ret, 0)
        mock_service.search_videos.assert_called_with(
            "python", 5, channelId="channel123", order="date", videoDuration="short"
        )
        output = sys.stdout.getvalue()
        self.assertIn('"items": []', output)

    @patch('yt_tools.cli._get_service')
    def test_details_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_video_details.return_value = {
            'items': [{
                'snippet': {
                    'title': 'Detailed Video',
                    'channelTitle': 'Channel X',
                    'publishedAt': '2023-01-01',
                    'description': 'A description'
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '50'
                }
            }]
        }
        
        args = argparse.Namespace(video_id="v123", json=False)
        
        ret = cli.cmd_details(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_video_details.assert_called_with("v123")
        output = sys.stdout.getvalue()
        self.assertIn("Detailed Video", output)
        self.assertIn("1000", output)

    @patch('yt_tools.cli._get_service')
    def test_channel_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_channel_details.return_value = {
            'items': [{
                'snippet': {
                    'title': 'My Channel',
                    'description': 'Channel Desc'
                },
                'statistics': {
                    'subscriberCount': '500',
                    'videoCount': '10',
                    'viewCount': '5000'
                }
            }]
        }
        
        args = argparse.Namespace(channel_id="c123", json=False)
        
        ret = cli.cmd_channel(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_channel_details.assert_called_with("c123")
        output = sys.stdout.getvalue()
        self.assertIn("My Channel", output)
        self.assertIn("500", output)

    @patch('yt_tools.cli._get_service')
    def test_transcript_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock transcript segments
        mock_service.get_video_transcript.return_value = [
            {'text': 'Hello world', 'start': 0.0},
            {'text': 'Next line', 'start': 2.5}
        ]
        mock_service.format_time.side_effect = lambda ms: f"{ms}ms"
        
        args = argparse.Namespace(video_id="v123", language="en", json=False)
        
        ret = cli.cmd_transcript(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_video_transcript.assert_called_with("v123", "en")
        output = sys.stdout.getvalue()
        self.assertIn("Hello world", output)

    @patch('yt_tools.cli._get_service')
    def test_comments_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_video_comments.return_value = {
            'items': [{
                'snippet': {
                    'topLevelComment': {
                        'snippet': {
                            'authorDisplayName': 'User1',
                            'textDisplay': 'Great video!'
                        }
                    }
                }
            }]
        }
        
        args = argparse.Namespace(
            video_id="v123",
            max_results=20,
            order='relevance',
            replies=False,
            json=False
        )
        
        ret = cli.cmd_comments(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_video_comments.assert_called_with(
            "v123", 20, order='relevance', includeReplies=False
        )
        output = sys.stdout.getvalue()
        self.assertIn("User1", output)
        self.assertIn("Great video!", output)

    @patch('yt_tools.cli._get_service')
    def test_related_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_related_videos.return_value = {
            'items': [
                {
                    'id': {'videoId': 'rel1'},
                    'snippet': {
                        'title': 'Related Video',
                        'channelTitle': 'Another Channel'
                    }
                }
            ]
        }
        
        args = argparse.Namespace(video_id="v123", max_results=10, json=False)
        
        ret = cli.cmd_related(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_related_videos.assert_called_with("v123", 10)
        output = sys.stdout.getvalue()
        self.assertIn("Related Video", output)

    @patch('yt_tools.cli._get_service')
    def test_trending_command(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_service.get_trending_videos.return_value = {
            'items': [
                {
                    'id': 'trend1',
                    'snippet': {'title': 'Trending Now'},
                    'statistics': {'viewCount': '1000000'}
                }
            ]
        }
        
        args = argparse.Namespace(region="US", max_results=10, json=False)
        
        ret = cli.cmd_trending(args)
        
        self.assertEqual(ret, 0)
        mock_service.get_trending_videos.assert_called_with("US", 10)
        output = sys.stdout.getvalue()
        self.assertIn("Trending Now", output)

    @patch("yt_tools.cli._load_api_key_environment")
    @patch("yt_tools.cli.authorize")
    def test_authorize_does_not_search_dotenv_locations(self, mock_authorize, mock_load_environment):
        result = cli.main([
            "authorize",
            "--client-secrets", "/source/client.json",
        ])

        self.assertEqual(result, 0)
        mock_load_environment.assert_not_called()

    @patch("yt_tools.cli.authorize")
    def test_authorize_command_returns_an_actionable_nonzero_error(self, mock_authorize):
        mock_authorize.side_effect = AuthorizationError("Authorization was denied. Try again.")

        result = cli.main([
            "authorize",
            "--client-secrets", "/source/client.json",
        ])

        self.assertEqual(result, 1)
        self.assertIn("Authorization was denied. Try again.", sys.stderr.getvalue())
        self.assertNotIn("Unexpected", sys.stderr.getvalue())

    @patch("yt_tools.cli.authorize")
    def test_authorize_command_stores_credentials_at_resolved_destinations(self, mock_authorize):
        result = cli.main([
            "authorize",
            "--client-secrets", "/source/client.json",
            "--client-config-file", "/stored/client.json",
            "--token-file", "/stored/token.json",
        ])

        self.assertEqual(result, 0)
        mock_authorize.assert_called_once_with(
            "/source/client.json",
            Path("/stored/client.json"),
            Path("/stored/token.json"),
        )
        self.assertIn("Authorization complete", sys.stdout.getvalue())

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_report_types_outputs_agent_selectable_json(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reportTypes.return_value.list.return_value.execute.return_value = {
            "reportTypes": [{
                "id": "channel_reach_basic_a42",
                "name": "Reach Basic",
                "systemManaged": False,
            }]
        }

        result = cli.main([
            "reporting", "report-types",
            "--token-file", "/secure/token.json",
        ])

        self.assertEqual(result, 0)
        load_credentials.assert_called_once_with(Path("/secure/token.json"))
        build_api.assert_called_once_with(load_credentials.return_value)
        self.assertEqual(json.loads(sys.stdout.getvalue()), {
            "availability": "available",
            "reportTypes": [{
                "id": "channel_reach_basic_a42",
                "name": "Reach Basic",
                "systemManaged": False,
                "isReachReport": True,
            }],
        })

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_authorization_failure_is_distinct_from_empty_availability(
        self,
        load_credentials,
        build_api,
    ):
        load_credentials.side_effect = AuthorizationError(
            "Stored authorization refresh failed. Run yt-tools authorize again."
        )

        result = cli.main(["reporting", "report-types"])

        self.assertEqual(result, 1)
        self.assertEqual(sys.stdout.getvalue(), "")
        self.assertIn("refresh failed", sys.stderr.getvalue())
        self.assertIn("authorize again", sys.stderr.getvalue())
        build_api.assert_not_called()

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_create_returns_upstream_identity(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.jobs.return_value.create.return_value.execute.return_value = {
            "id": "job-123",
            "reportTypeId": "channel_basic_a3",
            "name": "Daily channel export",
            "createTime": "2026-08-21T10:00:00Z",
        }

        result = cli.main([
            "reporting", "jobs", "create",
            "--report-type-id", "channel_basic_a3",
            "--name", "Daily channel export",
            "--token-file", "/secure/token.json",
        ])

        self.assertEqual(result, 0)
        load_credentials.assert_called_once_with(Path("/secure/token.json"))
        build_api.assert_called_once_with(load_credentials.return_value)
        self.assertEqual(json.loads(sys.stdout.getvalue()), {
            "id": "job-123",
            "reportTypeId": "channel_basic_a3",
            "name": "Daily channel export",
            "createTime": "2026-08-21T10:00:00Z",
        })

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_client_failure_is_actionable(
        self,
        load_credentials,
        build_api,
    ):
        build_api.side_effect = ReportingDiscoveryError(
            "Failed to initialize the YouTube Reporting API client: unavailable"
        )

        result = cli.main([
            "reporting", "jobs", "create",
            "--report-type-id", "channel_basic_a3",
            "--name", "Daily export",
        ])

        self.assertEqual(result, 1)
        self.assertIn("Failed to initialize", sys.stderr.getvalue())
        self.assertNotIn("Unexpected", sys.stderr.getvalue())

    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_create_rejects_empty_input_before_authorization(
        self,
        load_credentials,
    ):
        for option in ("--report-type-id", "--name"):
            with self.subTest(option=option):
                with self.assertRaises(SystemExit) as raised:
                    arguments = [
                        "reporting", "jobs", "create",
                        "--report-type-id", "channel_basic_a3",
                        "--name", "Daily export",
                    ]
                    arguments[arguments.index(option) + 1] = "   "
                    cli.main(arguments)
                self.assertEqual(raised.exception.code, 2)
        load_credentials.assert_not_called()

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_jobs_list_returns_lifecycle_metadata(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.jobs.return_value.list.return_value.execute.return_value = {
            "jobs": [{
                "id": "job-123",
                "reportTypeId": "channel_basic_a3",
                "name": "Daily channel export",
                "createTime": "2026-08-21T10:00:00Z",
                "expireTime": "2026-09-21T10:00:00Z",
                "systemManaged": False,
            }]
        }

        result = cli.main(["reporting", "jobs", "list"])

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(sys.stdout.getvalue())["jobs"][0]["id"], "job-123")
        self.assertEqual(
            json.loads(sys.stdout.getvalue())["jobs"][0]["expireTime"],
            "2026-09-21T10:00:00Z",
        )

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_reports_list_returns_generated_file_metadata(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.jobs.return_value.reports.return_value.list.return_value.execute.return_value = {
            "reports": [{
                "id": "report-123",
                "jobId": "job-123",
                "startTime": "2026-08-19T00:00:00Z",
                "endTime": "2026-08-20T00:00:00Z",
                "createTime": "2026-08-20T06:00:00Z",
                "downloadUrl": "https://youtube.example/report-123",
            }]
        }

        result = cli.main([
            "reporting", "jobs", "reports", "list",
            "--job-id", "job-123",
            "--token-file", "/secure/token.json",
        ])

        self.assertEqual(result, 0)
        load_credentials.assert_called_once_with(Path("/secure/token.json"))
        output = json.loads(sys.stdout.getvalue())
        self.assertEqual(output["availability"], "available")
        self.assertEqual(output["reports"][0]["id"], "report-123")
        self.assertEqual(
            output["reports"][0]["downloadUrl"],
            "https://youtube.example/report-123",
        )

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_reports_unknown_job_is_actionable(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.jobs.return_value.reports.return_value.list.return_value.execute.side_effect = HttpError(
            MagicMock(status=404, reason="Not Found"),
            json.dumps({"error": {"message": "Reporting job not found."}}).encode(),
        )

        result = cli.main([
            "reporting", "jobs", "reports", "list",
            "--job-id", "unknown-job",
        ])

        self.assertEqual(result, 1)
        self.assertEqual(sys.stdout.getvalue(), "")
        self.assertIn("request failed (404)", sys.stderr.getvalue())
        self.assertIn("Reporting job not found", sys.stderr.getvalue())

    @patch("yt_tools.cli.build_reporting_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_reporting_job_delete_outputs_explicit_success(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.jobs.return_value.delete.return_value.execute.return_value = None

        result = cli.main([
            "reporting", "jobs", "delete",
            "--job-id", "job-123",
            "--token-file", "/secure/token.json",
        ])

        self.assertEqual(result, 0)
        api.jobs.return_value.delete.assert_called_once_with(jobId="job-123")
        self.assertEqual(json.loads(sys.stdout.getvalue()), {
            "id": "job-123",
            "status": "deleted",
        })

    @patch("yt_tools.cli.build_data_api")
    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_query_outputs_named_json(
        self,
        load_credentials,
        build_api,
        build_data_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "country", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [["US", 20]],
        }

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--dimensions", "country",
            "--filters", "country==US",
            "--sort=-views",
            "--max-results", "50",
            "--start-index", "1",
            "--currency", "USD",
            "--token-file", "/secure/token.json",
        ])

        self.assertEqual(result, 0)
        load_credentials.assert_called_once_with(Path("/secure/token.json"))
        build_api.assert_called_once_with(load_credentials.return_value)
        api.reports.return_value.query.assert_called_once_with(
            ids="channel==MINE",
            startDate="2026-08-01",
            endDate="2026-08-02",
            metrics="views",
            dimensions="country",
            filters="country==US",
            sort="-views",
            maxResults=50,
            startIndex=1,
            currency="USD",
        )
        self.assertEqual(json.loads(sys.stdout.getvalue()), {
            "requestedRange": {
                "startDate": "2026-08-01",
                "endDate": "2026-08-02",
            },
            "returnedRange": None,
            "columns": [
                {"name": "country", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [{"country": "US", "views": 20}],
        })
        build_data_api.assert_not_called()

    @patch("yt_tools.cli.build_data_api")
    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_query_explicitly_enriches_video_rows_with_current_metadata(
        self,
        load_credentials,
        build_analytics_api,
        build_data_api,
    ):
        analytics_api = MagicMock()
        build_analytics_api.return_value = analytics_api
        analytics_api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "video", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [["video-1", 20]],
        }
        data_api = MagicMock()
        build_data_api.return_value = data_api
        data_api.videos.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "video-1",
                "snippet": {"title": "Current title"},
                "contentDetails": {"duration": "PT1M"},
                "status": {"privacyStatus": "public"},
            }]
        }

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--dimensions", "video",
            "--enrich-video-metadata",
        ])

        self.assertEqual(result, 0)
        build_data_api.assert_called_once_with(load_credentials.return_value)
        self.assertEqual(json.loads(sys.stdout.getvalue())["rows"], [{
            "video": "video-1",
            "views": 20,
            "videoMetadata": {
                "availability": "available",
                "snippet": {"title": "Current title"},
                "contentDetails": {"duration": "PT1M"},
                "status": {"privacyStatus": "public"},
            },
        }])

    @patch("yt_tools.cli.build_data_api")
    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_metadata_enrichment_requires_the_video_dimension_before_api_access(
        self,
        load_credentials,
        build_analytics_api,
        build_data_api,
    ):
        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--dimensions", "day",
            "--enrich-video-metadata",
        ])

        self.assertEqual(result, 1)
        self.assertIn(
            "--enrich-video-metadata requires the video dimension",
            sys.stderr.getvalue(),
        )
        load_credentials.assert_not_called()
        build_analytics_api.assert_not_called()
        build_data_api.assert_not_called()

    @patch("yt_tools.cli.build_data_api")
    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_metadata_request_failure_is_actionable_and_returns_no_partial_result(
        self,
        load_credentials,
        build_analytics_api,
        build_data_api,
    ):
        analytics_api = MagicMock()
        build_analytics_api.return_value = analytics_api
        analytics_api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "video", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [["video-1", 20]],
        }
        data_api = MagicMock()
        build_data_api.return_value = data_api
        data_api.videos.return_value.list.return_value.execute.side_effect = HttpError(
            MagicMock(status=403, reason="Forbidden"),
            json.dumps({
                "error": {
                    "message": "Data API quota exceeded.",
                    "errors": [{"reason": "quotaExceeded"}],
                }
            }).encode(),
        )

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--dimensions", "video",
            "--enrich-video-metadata",
        ])

        self.assertEqual(result, 1)
        self.assertEqual(sys.stdout.getvalue(), "")
        self.assertIn("YouTube Data API request failed (403)", sys.stderr.getvalue())
        self.assertIn("Data API quota exceeded.", sys.stderr.getvalue())
        self.assertIn("quotaExceeded", sys.stderr.getvalue())
        self.assertNotIn("Unexpected", sys.stderr.getvalue())

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_query_outputs_explicit_csv_in_column_order(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "day", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
                {"name": "note", "columnType": "DIMENSION", "dataType": "STRING"},
            ],
            "rows": [
                ["2026-08-01", 20, ""],
                ["2026-08-02", None, "quoted, value"],
            ],
        }

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--dimensions", "day",
            "--format", "csv",
        ])

        self.assertEqual(result, 0)
        self.assertEqual(list(csv.reader(StringIO(sys.stdout.getvalue()))), [
            ["day", "views", "note"],
            ["2026-08-01", "20", ""],
            ["2026-08-02", "", "quoted, value"],
        ])

    def test_enriched_csv_serializes_video_metadata_as_json(self):
        cli.print_analytics_csv({
            "columns": [
                {"name": "video"},
                {"name": "videoMetadata"},
            ],
            "rows": [{
                "video": "video-1",
                "videoMetadata": {
                    "availability": "available",
                    "snippet": {"title": "Current title"},
                },
            }],
        })

        rows = list(csv.reader(StringIO(sys.stdout.getvalue())))
        self.assertEqual(rows[0], ["video", "videoMetadata"])
        self.assertEqual(rows[1][0], "video-1")
        self.assertEqual(json.loads(rows[1][1]), {
            "availability": "available",
            "snippet": {"title": "Current title"},
        })

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_empty_analytics_query_outputs_header_only_csv(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [],
        }

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
            "--format", "csv",
        ])

        self.assertEqual(result, 0)
        self.assertEqual(sys.stdout.getvalue(), "views\n")

    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_dates_and_metrics_are_required(self, load_credentials):
        with self.assertRaises(SystemExit) as raised:
            cli.main([
                "analytics", "query",
                "--channel", "MINE",
            ])

        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn("--start-date", sys.stderr.getvalue())
        self.assertIn("--end-date", sys.stderr.getvalue())
        self.assertIn("--metrics", sys.stderr.getvalue())
        load_credentials.assert_not_called()

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_malformed_analytics_input_fails_before_credentials_or_api_request(
        self,
        load_credentials,
        build_api,
    ):
        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "not-a-date",
            "--end-date", "2026-08-02",
            "--metrics", "views",
        ])

        self.assertEqual(result, 1)
        self.assertIn("start date", sys.stderr.getvalue())
        load_credentials.assert_not_called()
        build_api.assert_not_called()

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_upstream_failure_returns_nonzero_with_google_detail(
        self,
        load_credentials,
        build_api,
    ):
        api = MagicMock()
        build_api.return_value = api
        api.reports.return_value.query.return_value.execute.side_effect = HttpError(
            MagicMock(status=403, reason="Forbidden"),
            json.dumps({
                "error": {
                    "message": "Quota exceeded for quota metric Queries.",
                    "errors": [{"reason": "quotaExceeded"}],
                }
            }).encode(),
        )

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
        ])

        self.assertEqual(result, 1)
        self.assertIn("403", sys.stderr.getvalue())
        self.assertIn("Quota exceeded", sys.stderr.getvalue())
        self.assertIn("quotaExceeded", sys.stderr.getvalue())

    @patch("yt_tools.cli.build_analytics_api")
    @patch("yt_tools.cli.load_authorized_credentials")
    def test_analytics_authorization_failure_returns_actionable_nonzero_error(
        self,
        load_credentials,
        build_api,
    ):
        load_credentials.side_effect = AuthorizationError(
            "Stored authorization refresh failed. Run yt-tools authorize again."
        )

        result = cli.main([
            "analytics", "query",
            "--channel", "MINE",
            "--start-date", "2026-08-01",
            "--end-date", "2026-08-02",
            "--metrics", "views",
        ])

        self.assertEqual(result, 1)
        self.assertIn("refresh failed", sys.stderr.getvalue())
        self.assertIn("authorize again", sys.stderr.getvalue())
        build_api.assert_not_called()

    def test_authorize_command_accepts_source_and_destination_overrides(self):
        args = cli.build_parser().parse_args([
            "authorize",
            "--client-secrets", "/source/client.json",
            "--client-config-file", "/stored/client.json",
            "--token-file", "/stored/token.json",
        ])

        self.assertEqual(args.cmd, "authorize")
        self.assertEqual(args.client_secrets, "/source/client.json")
        self.assertEqual(args.client_config_file, "/stored/client.json")
        self.assertEqual(args.token_file, "/stored/token.json")
        self.assertIs(args.func, cli.cmd_authorize)

    def test_version_command(self):
        # We can't easily test the version flag as it calls sys.exit
        # But we can test get_version
        v = cli.get_version()
        # Since we are mocking metadata in the module or running in env where it might be installed
        # this is just a sanity check that it returns a string
        self.assertIsInstance(v, str)

    @patch('yt_tools.cli._get_service')
    def test_error_handling(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.search_videos.side_effect = Exception("API Error")
        
        args = argparse.Namespace(
            query="test", max_results=10, channel_id=None,
            order=None, duration=None, json=False
        )
        
        with self.assertRaises(cli.ToolboxError):
            cli.cmd_search(args)

if __name__ == '__main__':
    unittest.main()
