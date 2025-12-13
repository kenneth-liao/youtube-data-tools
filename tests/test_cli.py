import argparse
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from yt_tools import cli

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
