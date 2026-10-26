import json
import unittest
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from yt_tools.video_update import (
    VideoUpdateError,
    build_snippet_update,
    update_video_metadata,
    validate_update_fields,
)


def current_snippet():
    return {
        "publishedAt": "2026-01-01T00:00:00Z",
        "channelId": "UC-owned",
        "title": "Old title",
        "description": "Old description",
        "thumbnails": {"default": {"url": "https://i.ytimg.com/x.jpg"}},
        "channelTitle": "Owner",
        "tags": ["old", "kept"],
        "categoryId": "28",
        "liveBroadcastContent": "none",
        "defaultLanguage": "en",
        "localized": {"title": "Old title", "description": "Old description"},
        "defaultAudioLanguage": "en-US",
    }


def data_api(snippet=None, owner="UC-owned", saved=None):
    api = MagicMock()
    items = [] if snippet is False else [{"id": "vid", "snippet": snippet or current_snippet()}]
    api.videos.return_value.list.return_value.execute.return_value = {"items": items}
    api.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": owner}]
    }
    api.videos.return_value.update.return_value.execute.return_value = {
        "id": "vid",
        "snippet": saved or {},
    }
    return api


def http_error(status, message):
    response = MagicMock(status=status, reason="Forbidden")
    content = json.dumps({"error": {"message": message}}).encode("utf-8")
    return HttpError(response, content)


class TestBuildSnippetUpdate(unittest.TestCase):
    def test_only_requested_fields_change_and_writable_fields_are_kept(self):
        snippet = build_snippet_update(current_snippet(), description="New")

        self.assertEqual(snippet["description"], "New")
        self.assertEqual(snippet["title"], "Old title")
        self.assertEqual(snippet["tags"], ["old", "kept"])
        self.assertEqual(snippet["categoryId"], "28")
        self.assertEqual(snippet["defaultLanguage"], "en")
        self.assertEqual(snippet["defaultAudioLanguage"], "en-US")

    def test_read_only_fields_are_not_sent(self):
        snippet = build_snippet_update(current_snippet(), title="New")

        for field in (
            "publishedAt",
            "channelId",
            "thumbnails",
            "channelTitle",
            "liveBroadcastContent",
            "localized",
        ):
            self.assertNotIn(field, snippet)

    def test_empty_tag_list_clears_tags(self):
        self.assertEqual(build_snippet_update(current_snippet(), tags=[])["tags"], [])

    def test_current_snippet_is_not_mutated(self):
        snippet = current_snippet()
        build_snippet_update(snippet, tags=["new"])

        self.assertEqual(snippet, current_snippet())


class TestUpdateVideoMetadata(unittest.TestCase):
    def test_preview_reports_changes_without_writing(self):
        api = data_api()

        result = update_video_metadata(
            api, "vid", description="New", tags=["old", "new"]
        )

        self.assertFalse(result["applied"])
        self.assertEqual(result["videoId"], "vid")
        self.assertEqual(
            result["changes"],
            {
                "description": {"current": "Old description", "proposed": "New"},
                "tags": {"current": ["old", "kept"], "proposed": ["old", "new"]},
            },
        )
        api.videos.return_value.list.assert_called_once_with(part="snippet", id="vid")
        api.videos.return_value.update.assert_not_called()

    def test_unchanged_requested_values_are_not_reported(self):
        result = update_video_metadata(data_api(), "vid", title="Old title")

        self.assertEqual(result["changes"], {})

    def test_missing_current_tags_compare_as_empty(self):
        snippet = current_snippet()
        del snippet["tags"]

        result = update_video_metadata(data_api(snippet), "vid", tags=[])

        self.assertEqual(result["changes"], {})

    def test_apply_sends_the_full_snippet_and_returns_saved_values(self):
        saved = {**current_snippet(), "title": "New title"}
        api = data_api(saved=saved)

        result = update_video_metadata(api, "vid", title="New title", apply=True)

        api.videos.return_value.update.assert_called_once_with(
            part="snippet",
            body={
                "id": "vid",
                "snippet": {
                    "title": "New title",
                    "description": "Old description",
                    "tags": ["old", "kept"],
                    "categoryId": "28",
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en-US",
                },
            },
        )
        self.assertTrue(result["applied"])
        self.assertEqual(
            result["saved"],
            {"title": "New title", "description": "Old description", "tags": ["old", "kept"]},
        )

    def test_apply_without_changes_makes_no_write(self):
        api = data_api()

        result = update_video_metadata(api, "vid", title="Old title", apply=True)

        self.assertFalse(result["applied"])
        api.videos.return_value.update.assert_not_called()

    def test_unknown_video_is_actionable(self):
        with self.assertRaisesRegex(VideoUpdateError, "vid.*not found"):
            update_video_metadata(data_api(snippet=False), "vid", title="New")

    def test_video_owned_by_another_channel_is_rejected_before_writing(self):
        api = data_api(owner="UC-someone-else")

        with self.assertRaisesRegex(VideoUpdateError, "not owned by the authorized channel"):
            update_video_metadata(api, "vid", title="New", apply=True)

        api.videos.return_value.update.assert_not_called()

    def test_at_least_one_field_is_required(self):
        api = data_api()

        with self.assertRaisesRegex(VideoUpdateError, "at least one"):
            update_video_metadata(api, "vid")

        api.videos.return_value.list.assert_not_called()

    def test_blank_title_is_rejected_before_any_api_call(self):
        api = data_api()

        with self.assertRaisesRegex(VideoUpdateError, "title cannot be empty"):
            update_video_metadata(api, "vid", title="  ")

        api.videos.assert_not_called()
        api.channels.assert_not_called()

    def test_validation_returns_only_requested_fields(self):
        self.assertEqual(
            validate_update_fields(description="New", tags=[]),
            {"description": "New", "tags": []},
        )

    def test_google_api_errors_are_actionable(self):
        api = data_api()
        api.videos.return_value.update.return_value.execute.side_effect = http_error(
            400, "The request metadata specifies an invalid video title."
        )

        with self.assertRaisesRegex(
            VideoUpdateError, r"YouTube Data API request failed \(400\).*invalid video title"
        ):
            update_video_metadata(api, "vid", title="<bad>", apply=True)


if __name__ == "__main__":
    unittest.main()
