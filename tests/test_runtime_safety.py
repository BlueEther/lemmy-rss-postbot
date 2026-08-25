import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / 'lemmy-rss-pybot.py'
SPEC = importlib.util.spec_from_file_location('lemmy_rss_pybot_runtime', MODULE_PATH)
BOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOT)


class RuntimeSafetyTests(unittest.TestCase):
    def test_interval_and_time_are_aliases(self):
        for option in ('--interval', '--time'):
            with self.subTest(option=option), patch('sys.argv', ['bot', option, '7']):
                self.assertEqual(BOT.parse_args().interval, 7)

    def test_compose_environment_supplies_persistent_paths(self):
        environment = {
            'LEMMY_BOT_FEEDS': '/app/rss_feeds.json',
            'LEMMY_BOT_LOG': '/app/data/lemmy_bot.log',
            'LEMMY_BOT_STATE': '/app/data/seen_articles.json',
        }
        with patch.dict(BOT.os.environ, environment), patch('sys.argv', ['bot']):
            args = BOT.parse_args()

        self.assertEqual(args.feeds, '/app/rss_feeds.json')
        self.assertEqual(args.log, '/app/data/lemmy_bot.log')
        self.assertEqual(args.state, '/app/data/seen_articles.json')

    def test_include_regex_matches_only_the_url_path(self):
        feed = {'_include_pattern': BOT.regex.compile(r'^/technology/')}

        self.assertTrue(BOT.article_matches_include_regex(feed, 'https://example.com/technology/story?id=1'))
        self.assertFalse(BOT.article_matches_include_regex(feed, 'https://technology.example.com/sports/story'))

    def test_invalid_include_regex_is_rejected_during_loading(self):
        config = [{
            'feed_url': 'https://example.com/rss',
            'community': 'news@example.com',
            'include_regex': '[',
        }]
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / 'feeds.json'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            with self.assertRaises(ValueError):
                BOT.load_feeds(config_path)

    @patch.object(BOT.requests, 'post')
    def test_failed_post_raises_instead_of_being_marked_seen(self, post):
        post.return_value = Mock(status_code=500, text='server error')

        with self.assertRaisesRegex(Exception, 'Failed to create post'):
            BOT.create_post('https://lemmy.example', 'jwt', 1, 'news', 'Title', 'https://example.com/story')

    def test_test_mode_does_not_load_credentials_or_post(self):
        config = [{
            'feed_url': 'https://example.com/rss',
            'community': 'news@example.com',
            'keywords': ['science'],
        }]
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / 'feeds.json'
            log_path = Path(directory) / 'test.log'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            argv = ['bot', '--feeds', str(config_path), '--log', str(log_path), '--test']
            with (
                patch('sys.argv', argv),
                patch.object(BOT, 'show_banner'),
                patch.object(BOT, 'load_credentials') as load_credentials,
                patch.object(BOT, 'create_post') as create_post,
            ):
                BOT.main()

            load_credentials.assert_not_called()
            create_post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
