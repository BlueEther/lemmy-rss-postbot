import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / 'lemmy-rss-pybot.py'
SPEC = importlib.util.spec_from_file_location('lemmy_rss_pybot', MODULE_PATH)
BOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOT)


class KeywordTests(unittest.TestCase):
    def test_short_and_phrase_keywords_match_title_or_summary(self):
        keywords = BOT.normalize_keywords(['AI', 'machine learning'])

        self.assertEqual(
            BOT.article_matches_keywords({'title': 'AI update', 'summary': ''}, keywords),
            (True, 'ai'),
        )
        self.assertEqual(
            BOT.article_matches_keywords(
                {'title': 'Research update', 'summary': 'Machine Learning breakthrough'},
                keywords,
            ),
            (True, 'machine learning'),
        )
        self.assertEqual(
            BOT.article_matches_keywords({'title': 'Sailing report', 'summary': ''}, keywords),
            (False, None),
        )

    def test_per_feed_keywords_override_global_keywords(self):
        self.assertEqual(BOT.get_feed_keywords({'_keywords': {'python'}}, {'science'}), {'python'})
        self.assertEqual(BOT.get_feed_keywords({}, {'science'}), {'science'})

    def test_feed_details_contain_community_feed_and_keywords(self):
        feed = {
            'community': 'technology@example.com',
            'feed_url': 'https://example.com/rss',
            '_keywords': {'python', 'ai'},
        }

        self.assertEqual(
            BOT.format_feed_details(feed, {'fallback'}),
            'Community: technology@example.com : '
            'RSS Feed: https://example.com/rss : Key Words: ai, python',
        )
        self.assertEqual(
            BOT.format_skipping_feed_log(feed, {'fallback'}),
            '[Skipping feed] Community: technology@example.com : '
            'RSS Feed: https://example.com/rss : Key Words: ai, python',
        )

    def test_feed_loader_rejects_empty_keywords(self):
        config = [{
            'feed_url': 'https://example.com/rss',
            'community': 'news@example.com',
            'keywords': [],
        }]
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / 'feeds.json'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            with self.assertRaises(ValueError):
                BOT.load_feeds(config_path)


if __name__ == '__main__':
    unittest.main()
