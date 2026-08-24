import unittest
from unittest.mock import MagicMock

from yt_tools.core import YouTubeService


class TestChannelIdentity(unittest.TestCase):
    def setUp(self):
        self.service = YouTubeService.__new__(YouTubeService)
        self.service.youtube = MagicMock()
        self.service.youtube.channels.return_value.list.return_value.execute.return_value = {
            "items": []
        }

    def test_raw_channel_id_uses_the_id_parameter(self):
        channel_id = "UCabcdefghijklmnopqrstuv"

        self.service.get_channel_details(channel_id)

        self.service.youtube.channels.return_value.list.assert_called_once_with(
            part="snippet,statistics",
            id=channel_id,
        )

    def test_channel_url_uses_the_full_channel_id(self):
        channel_id = "UCabcdefghijklmnopqrstuv"

        self.service.get_channel_details(
            f"https://www.youtube.com/channel/{channel_id}"
        )

        self.service.youtube.channels.return_value.list.assert_called_once_with(
            part="snippet,statistics",
            id=channel_id,
        )

    def test_handle_uses_the_for_handle_parameter(self):
        self.service.get_channel_details("@example.handle")

        self.service.youtube.channels.return_value.list.assert_called_once_with(
            part="snippet,statistics",
            forHandle="@example.handle",
        )

    def test_handle_url_uses_the_for_handle_parameter(self):
        self.service.get_channel_details(
            "https://www.youtube.com/@example.handle"
        )

        self.service.youtube.channels.return_value.list.assert_called_once_with(
            part="snippet,statistics",
            forHandle="@example.handle",
        )

    def test_unknown_identity_names_accepted_shapes_before_api_access(self):
        with self.assertRaisesRegex(
            ValueError,
            r"raw UC.*?/channel/UC.*?@handle.*?handle URL",
        ) as raised:
            self.service.get_channel_details("not-a-channel")

        self.assertNotIn("not found", str(raised.exception))
        self.service.youtube.channels.return_value.list.assert_not_called()


if __name__ == "__main__":
    unittest.main()
