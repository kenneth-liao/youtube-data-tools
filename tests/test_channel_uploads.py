import argparse
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from yt_tools import cli
from yt_tools.core import YouTubeService

CHANNEL_ID = "UCabcdefghijklmnopqrstuv"
PLAYLIST_ID = "UUabcdefghijklmnopqrstuv"


def upload(n):
    return {
        "snippet": {"title": f"Video {n}"},
        "contentDetails": {"videoId": f"vid{n:08d}", "videoPublishedAt": "2026-01-01T00:00:00Z"},
    }


class TestChannelUploads(unittest.TestCase):
    def setUp(self):
        self.service = YouTubeService.__new__(YouTubeService)
        self.service.youtube = MagicMock()
        self.channels = self.service.youtube.channels.return_value.list
        self.playlist = self.service.youtube.playlistItems.return_value.list
        self.channels.return_value.execute.return_value = {
            "items": [{"id": CHANNEL_ID, "contentDetails": {"relatedPlaylists": {"uploads": PLAYLIST_ID}}}]
        }

    def test_reads_the_uploads_playlist_and_never_searches(self):
        self.playlist.return_value.execute.return_value = {"items": [upload(1), upload(2)]}

        result = self.service.get_channel_uploads(CHANNEL_ID, 25)

        self.channels.assert_called_once_with(part="contentDetails", id=CHANNEL_ID)
        self.playlist.assert_called_once_with(part="snippet,contentDetails", playlistId=PLAYLIST_ID, maxResults=25)
        self.service.youtube.search.assert_not_called()
        self.assertEqual(result["channelId"], CHANNEL_ID)
        self.assertEqual(result["uploadsPlaylistId"], PLAYLIST_ID)
        self.assertEqual([i["contentDetails"]["videoId"] for i in result["items"]], ["vid00000001", "vid00000002"])

    def test_a_handle_is_looked_up_by_handle(self):
        self.playlist.return_value.execute.return_value = {"items": []}

        self.service.get_channel_uploads("@somebody", 5)

        self.channels.assert_called_once_with(part="contentDetails", forHandle="@somebody")

    def test_more_than_fifty_uploads_are_read_in_pages(self):
        self.playlist.return_value.execute.side_effect = [
            {"items": [upload(n) for n in range(50)], "nextPageToken": "page2"},
            {"items": [upload(n) for n in range(50, 100)], "nextPageToken": "page3"},
        ]

        result = self.service.get_channel_uploads(CHANNEL_ID, 60)

        self.assertEqual(len(result["items"]), 60)
        self.assertEqual(self.playlist.call_count, 2)
        self.assertEqual(self.playlist.call_args_list[1].kwargs, {
            "part": "snippet,contentDetails", "playlistId": PLAYLIST_ID, "maxResults": 10, "pageToken": "page2",
        })

    def test_a_short_channel_stops_at_its_last_page(self):
        self.playlist.return_value.execute.return_value = {"items": [upload(1)]}

        result = self.service.get_channel_uploads(CHANNEL_ID, 200)

        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(self.playlist.call_count, 1)

    def test_an_unknown_channel_returns_no_items_and_reads_no_playlist(self):
        self.channels.return_value.execute.return_value = {"items": []}

        result = self.service.get_channel_uploads(CHANNEL_ID, 25)

        self.assertEqual(result, {"items": []})
        self.playlist.assert_not_called()

    def test_zero_results_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.get_channel_uploads(CHANNEL_ID, 0)


class TestUploadsCommand(unittest.TestCase):
    def setUp(self):
        self.held, sys.stdout = sys.stdout, StringIO()
        self.held_err, sys.stderr = sys.stderr, StringIO()

    def tearDown(self):
        sys.stdout = self.held
        sys.stderr = self.held_err

    @patch("yt_tools.cli._get_service")
    def test_lists_each_upload_with_its_id_and_date(self, mock_get_service):
        service = mock_get_service.return_value
        service.get_channel_uploads.return_value = {
            "channelId": CHANNEL_ID, "uploadsPlaylistId": PLAYLIST_ID, "items": [upload(1), upload(2)],
        }

        ret = cli.cmd_uploads(argparse.Namespace(channel_id=CHANNEL_ID, max_results=25, json=False))

        self.assertEqual(ret, 0)
        service.get_channel_uploads.assert_called_with(CHANNEL_ID, 25)
        output = sys.stdout.getvalue()
        self.assertIn("Video 1 (ID: vid00000001)", output)
        self.assertIn("2026-01-01", output)

    @patch("yt_tools.cli._get_service")
    def test_an_unknown_channel_is_an_error(self, mock_get_service):
        mock_get_service.return_value.get_channel_uploads.return_value = {"items": []}

        with self.assertRaises(cli.ToolboxError) as raised:
            cli.cmd_uploads(argparse.Namespace(channel_id=CHANNEL_ID, max_results=25, json=False))

        self.assertIn("not found", str(raised.exception))

    def test_help_gives_the_identity_shapes_and_the_quota_cost(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["uploads", "-h"])

        self.assertEqual(raised.exception.code, 0)
        output = sys.stdout.getvalue()
        for text in ("raw UC", "@handle", "--max-results", "2 quota units"):
            with self.subTest(text=text):
                self.assertIn(text, output)

    def test_the_command_is_in_the_short_and_full_docs(self):
        self.assertEqual(cli.main([]), 0)
        self.assertIn("uploads", sys.stdout.getvalue())
        self.assertEqual(cli.main(["docs"]), 0)
        self.assertIn("yt-tools uploads <channel_id>", sys.stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
