import unittest
from unittest.mock import MagicMock, patch

from yt_tools.video_metadata import build_data_api, enrich_video_rows


class TestVideoMetadataEnrichment(unittest.TestCase):
    def test_data_api_client_uses_authorized_youtube_v3(self):
        credentials = MagicMock()
        api = MagicMock()

        with patch("yt_tools.video_metadata.build", return_value=api) as build:
            result = build_data_api(credentials)

        self.assertIs(result, api)
        build.assert_called_once_with(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def test_duplicate_video_ids_are_looked_up_once_in_api_sized_batches(self):
        api = MagicMock()
        requests = api.videos.return_value.list.return_value.execute
        requests.side_effect = [
            {"items": [{"id": f"video-{index}"} for index in range(50)]},
            {"items": [{"id": "video-50"}]},
        ]
        rows = [{"video": f"video-{index}", "views": index} for index in range(51)]
        rows.append({"video": "video-0", "views": 100})
        result = {
            "columns": [{"name": "video"}],
            "rows": rows,
        }

        enriched = enrich_video_rows(api, result)

        self.assertEqual(api.videos.return_value.list.call_count, 2)
        api.videos.return_value.list.assert_any_call(
            part="snippet,contentDetails,status",
            id=",".join(f"video-{index}" for index in range(50)),
        )
        api.videos.return_value.list.assert_any_call(
            part="snippet,contentDetails,status",
            id="video-50",
        )
        self.assertEqual(len(enriched["rows"]), 52)
        self.assertEqual(
            enriched["rows"][-1]["videoMetadata"]["availability"],
            "available",
        )

    def test_unavailable_metadata_keeps_the_analytics_row_and_video_id(self):
        api = MagicMock()
        api.videos.return_value.list.return_value.execute.return_value = {"items": []}
        result = {
            "columns": [
                {"name": "video", "columnType": "DIMENSION", "dataType": "STRING"},
                {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            ],
            "rows": [{"video": "deleted-video", "views": 12}],
        }

        enriched = enrich_video_rows(api, result)

        self.assertEqual(enriched["rows"], [{
            "video": "deleted-video",
            "views": 12,
            "videoMetadata": {"availability": "unavailable"},
        }])


if __name__ == "__main__":
    unittest.main()
