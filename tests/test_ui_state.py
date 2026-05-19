import unittest

from streamlit.testing.v1 import AppTest

from vocab_filter.ui_state import should_show_level_settings_placement


class LevelSettingsStateTest(unittest.TestCase):
    def test_placement_panel_only_shows_for_quick_assessment_source(self):
        self.assertTrue(should_show_level_settings_placement("快速测评结果", True))
        self.assertFalse(should_show_level_settings_placement("考试成绩换算", True))
        self.assertFalse(should_show_level_settings_placement("手动选择 CEFR", True))
        self.assertFalse(should_show_level_settings_placement("快速测评结果", False))

    def test_non_quick_level_sources_do_not_render_quick_assessment_shortcut(self):
        for source, expected_action in [
            ("考试成绩换算", "使用这个水平"),
            ("手动选择 CEFR", "使用这个等级"),
        ]:
            with self.subTest(source=source):
                at = AppTest.from_file("app.py", default_timeout=10).run()
                at.session_state["level_settings_inline_open"] = True
                at.session_state["level_source"] = source
                at.session_state["level_source_choice"] = source
                at.session_state["level_settings_show_placement"] = True
                at.run()

                button_labels = [button.label for button in at.button]
                self.assertIn(expected_action, button_labels)
                self.assertNotIn("开始快速测评", button_labels)

    def test_about_panel_does_not_repeat_dialog_title(self):
        at = AppTest.from_file("app.py", default_timeout=10).run()
        at.session_state["about_inline_open"] = True
        at.run()

        markdown_values = [markdown.value for markdown in at.markdown]
        self.assertFalse(any("关于 Vocab Filter" in value for value in markdown_values))

    def test_uploaded_file_uses_native_uploader_without_extra_clear_button(self):
        filename = "CET6_Vocab_really_long_uploaded_file_name_for_testing_visibility.csv"
        at = AppTest.from_file("app.py", default_timeout=10).run()

        at = at.file_uploader[0].upload(filename, b"word\nhello\n", "text/csv").run()

        self.assertEqual(at.file_uploader[0].key, "analysis_upload")
        self.assertFalse(any(button.key == "clear_analysis_upload" for button in at.button))
        self.assertFalse(any("vf-upload-file" in markdown.value for markdown in at.markdown))

        at = at.file_uploader[0].clear().run()

        self.assertIsNone(at.file_uploader[0].value)


if __name__ == "__main__":
    unittest.main()
