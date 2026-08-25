import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / 'lemmy-rss-pybot.py'
SPEC = importlib.util.spec_from_file_location('lemmy_rss_pybot_seen_state', MODULE_PATH)
BOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOT)


class SeenStateTests(unittest.TestCase):
    def test_persistent_state_survives_an_empty_log(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'seen.json'
            log_path = Path(directory) / 'bot.log'
            expected = {'https://example.com/article': 'Example article'}
            BOT.save_seen_articles(state_path, expected)
            log_path.write_text('', encoding='utf-8')

            self.assertEqual(BOT.load_seen_articles(state_path, log_path), expected)

    def test_existing_log_is_migrated_on_first_use(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'seen.json'
            log_path = Path(directory) / 'bot.log'
            log_path.write_text(
                '2026-08-25 10:00:00 Posted: Example article | '
                'https://example.com/article | Community: test\n',
                encoding='utf-8',
            )

            seen = BOT.load_seen_articles(state_path, log_path)

            self.assertEqual(seen, {'https://example.com/article': 'Example article'})
            self.assertTrue(state_path.exists())

    def test_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'seen.json'
            log_path = Path(directory) / 'bot.log'
            state_path.write_text('{not valid json', encoding='utf-8')

            with self.assertRaisesRegex(ValueError, 'Cannot read seen-article state'):
                BOT.load_seen_articles(state_path, log_path)


if __name__ == '__main__':
    unittest.main()
