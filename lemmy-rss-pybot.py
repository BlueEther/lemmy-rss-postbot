#!/usr/bin/env python3

"""
Lemmy RSS PyBot: A script to read RSS feeds and post new articles to Lemmy communities.

Features:
- Reads RSS feeds from a JSON file with associated communities.
- Posts new articles to specified Lemmy communities.
- Filters articles based on keywords specified via arguments or a file.
- Checks for new articles every specified interval.
- Uses a configuration file for settings and credentials.
- Keeps a log of posted articles with rotating logs.
- Supports command-line arguments for customization.
- Includes comprehensive error handling and logging.
"""

import feedparser
import requests
import time
import logging
import argparse
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import json
import sys
import random
from http.client import RemoteDisconnected
from urllib.error import URLError
import traceback
from logging.handlers import RotatingFileHandler
import regex  # Use 'regex' module instead of 're'
import unicodedata

# Color definitions using ANSI escape codes
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
ENDC = "\033[0m"

# Custom log format with concise information
def color_log_message(level, message):
    if level == logging.INFO:
        return f"{GREEN}{BOLD}[+] INFO:{ENDC} {message}"
    elif level == logging.WARNING:
        return f"{YELLOW}{BOLD}[!] WARNING:{ENDC} {message}"
    elif level == logging.ERROR:
        return f"{RED}{BOLD}[X] ERROR:{ENDC} {message}"
    else:
        return message

class CustomFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return color_log_message(record.levelno, message)

# Setup logging with separate handlers for console and file
def setup_logging(log_file, verbose=False):
    """Set up logging for both console and file outputs. Console has ANSI colors, file does not."""

    # Formatter for console with ANSI color codes
    console_formatter = CustomFormatter('%(message)s')

    # Formatter for file without ANSI color codes (strip ANSI codes)
    file_formatter = logging.Formatter('%(asctime)s %(message)s')

    # File handler with rotation (without ANSI color codes)
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler (with ANSI color codes)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Create a root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear any existing handlers
    logger.handlers = []

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Helper function to strip ANSI color codes for file output
    def strip_ansi_codes(text):
        ansi_escape = regex.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', text)

    # Override the emit method for the file handler to strip ANSI codes
    original_emit = file_handler.emit

    def emit_without_ansi(record):
        record.msg = strip_ansi_codes(record.msg)
        original_emit(record)

    file_handler.emit = emit_without_ansi

# Function to log the articles posted
def log_posted_article(article_title, article_url, community_name):
    logging.info(f"Posted: {article_title} | {article_url} | Community: {community_name}")

# Function to remove log entries older than 2 days
def clean_old_logs(log_file):
    """Remove log entries older than 2 days."""
    two_days_ago = datetime.now() - timedelta(days=2)
    cleaned_lines = []

    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                # Extract the date using a regex pattern that looks for the timestamp
                match = regex.search(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                if match:
                    log_date_str = match.group(0)  # Extract the matched date string
                    try:
                        log_date = datetime.strptime(log_date_str, '%Y-%m-%d %H:%M:%S')
                        if log_date >= two_days_ago:
                            cleaned_lines.append(line)
                    except ValueError:
                        # Skip lines that have invalid date formats
                        continue
                else:
                    # If no date found, skip the line
                    continue
        # Overwrite the log file with cleaned entries
        with open(log_file, 'w') as f:
            f.writelines(cleaned_lines)

# Retry logic for fetching RSS feeds
def fetch_feed_with_retries(feed_url, max_retries=3, retry_delay=5):
    """Fetch an RSS feed with retry logic in case of connection failures."""
    retries = 0
    while retries < max_retries:
        try:
            feed_data = feedparser.parse(feed_url)
            if feed_data:
                return feed_data
        except (RemoteDisconnected, URLError, requests.exceptions.RequestException) as e:
            logging.error(f"Error fetching feed {feed_url}: {e}. Retrying {retries + 1}/{max_retries}...")
            retries += 1
            time.sleep(retry_delay)
    raise Exception(f"Failed to fetch feed {feed_url} after {max_retries} attempts.")

# banner
def show_banner():
    banner = f"""
 {RED}_                                     ____  ____ ____  
| |    ___ _ __ ___  _ __ ___  _   _  |  _ \\/ ___/ ___| 
| |   / _ \\ '_ ` _ \\| '_ ` _ \\| | | | | |_) \\___ \\___ \
| |__|  __/ | | | | | | | | | |_| | |  _ < ___) |__) |
|_____)___|_| |_| |_| |_| |_|\\__, | |_| \\_\\____/____/ 
                               |___/                 

 {BLUE} ____        ____        _   
|  _ \\ _   _| __ )  ___ | |_ 
| |_) | | | |  _ \\ / _ \\| __|
|  __/| |_| | |_) | (_) | |_ 
|_|    \\__, |____/ \\___/ \\__|
       |___/                 
 
 {BOLD}{GREEN}Version 1.34  - {ENDC} {BOLD}{YELLOW}Created By Dimitris Vagiakakos @sv1sjp - TuxHouse{ENDC}
"""
    print(banner)

def parse_args():
    parser = argparse.ArgumentParser(description='Lemmy RSS PyBot: Reads RSS feeds and posts new articles to Lemmy communities.')
    parser.add_argument('--feeds', type=str, default='rss_feeds.json', help='Path to RSS feeds JSON file.')
    parser.add_argument('--log', type=str, default='lemmy_bot.log', help='Path to log file.')
        # Accept the same option under two names but store as interval
    parser.add_argument('--interval', '--time', dest='interval', type=int, default=15,
                        help='Interval in minutes between feed checks (default: 15 minutes). Alias: --time')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('--keywords', type=str, help='Comma-separated list of keywords to filter articles.')
    parser.add_argument('--keywords-file', type=str, help='Path to a file containing keywords to filter articles.')
    parser.add_argument('--max_posts', type=int, default=2, help='Maximum number of posts per interval.')
    parser.add_argument('--simultaneously', type=int, help='Number of posts to make simultaneously in each community before sleeping.')
    parser.add_argument('--example', action='store_true', help='Show examples of the tool usage and exit.')
    parser.add_argument('--test', action='store_true', help='Test the configuration and exit.')
    return parser.parse_args()

def load_credentials():
    load_dotenv()
    lemmy_username = os.getenv('LEMMY_USERNAME')
    lemmy_password = os.getenv('LEMMY_PASSWORD')
    lemmy_instance_url = os.getenv('LEMMY_INSTANCE_URL')
    if not all([lemmy_username, lemmy_password, lemmy_instance_url]):
        raise ValueError(f"{RED}{BOLD}[X] ERROR:{ENDC} Please set LEMMY_USERNAME, LEMMY_PASSWORD, and LEMMY_INSTANCE_URL in your .env file.")
    return lemmy_username, lemmy_password, lemmy_instance_url.rstrip('/')

def load_feeds(feeds_file):
    with open(feeds_file, 'r') as f:
        feeds = json.load(f)
    return feeds

def load_keywords(keywords_arg, keywords_file):
    keywords = set()
    if keywords_arg:
        keywords.update([k.strip().lower() for k in keywords_arg.split(',') if k.strip()])
    if keywords_file:
        if os.path.exists(keywords_file):
            with open(keywords_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        keywords.add(line.strip().lower())
        else:
            logging.error(f"Keywords file '{keywords_file}' not found.")
    # Remove very short keywords to prevent false positives
    keywords = {k for k in keywords if len(k) > 3}
    return keywords

def lemmy_login(base_url, username, password):
    """Login to Lemmy and return the JWT token."""
    logging.info("Attempting to log in to Lemmy...")

    login_url = f'{base_url}/api/v3/user/login'
    data = {
        'username_or_email': username,
        'password': password
    }
    response = requests.post(login_url, json=data)
    if response.status_code == 200:
        jwt = response.json().get('jwt')
        if jwt:
            logging.info(f"Login successful!")
            return jwt
        else:
            raise Exception(f'Login failed: No JWT token received.')
    else:
        raise Exception(f'Login failed: {response.status_code} {response.text}')

def get_community_id(base_url, community_name, jwt):
    """Fetch the community ID using the community name."""
    community_url = f'{base_url}/api/v3/community'
    headers = {
        'Authorization': f'Bearer {jwt}'
    }
    params = {'name': community_name}
    response = requests.get(community_url, headers=headers, params=params)
    if response.status_code == 200:
        community_view = response.json().get('community_view')
        if community_view:
            community_id = community_view.get('community').get('id')
            return community_id
        else:
            raise Exception(f'Community "{community_name}" not found.')
    else:
        raise Exception(f'Error fetching community ID: {response.status_code} {response.text}')

def create_post(base_url, jwt, community_id, community_name, title, url):
    """Create a new link post in a Lemmy community.

    Returns (success_bool, response_json_or_text). On success response_json is parsed JSON when available.
    """
    try:
        post_url = f'{base_url}/api/v3/post'
        headers = {'Authorization': f'Bearer {jwt}'}
        data = {
            'community_id': community_id,
            'name': title,
            'url': url,
        }
        response = requests.post(post_url, headers=headers, json=data)
        if response.status_code == 200:
            log_posted_article(title, url, community_name)
            try:
                return True, response.json()
            except Exception:
                return True, response.text
        elif response.status_code == 401:
            logging.error('Unauthorized: JWT expired or invalid.')
            return False, response.text
        else:
            logging.error(f'Failed to create post: {response.status_code} {response.text}')
            return False, response.text
    except Exception as e:
        logging.error(f"Error posting article '{title}' to community '{community_name}': {e}")
        logging.debug(traceback.format_exc())
        return False, str(e)

def load_seen_articles(log_file):
    """Load seen articles from the log file by parsing log entries.

    Returns a dict mapping article_url -> set of community names where it was posted.
    Uses '*' in the set to indicate the article was posted but community not recorded (backwards compatibility).
    """
    seen_articles = {}
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                # Extract the article title, URL, and community from the log line
                match = regex.search(r'Posted: (.*?) \| (.*?) \| Community: (.*)', line)
                if match:
                    article_title = match.group(1).strip()
                    article_url = match.group(2).strip()
                    community = match.group(3).strip()
                    seen_articles.setdefault(article_url, set()).add(community)
                else:
                    # For backward compatibility with old logs that may not have community
                    match = regex.search(r'Posted: (.*?) \| (.*)', line)
                    if match:
                        article_title = match.group(1).strip()
                        article_url = match.group(2).strip()
                        # Mark as posted but community unknown
                        seen_articles.setdefault(article_url, set()).add('*')
    return seen_articles


def post_article_primary_and_crossposts(base_url, jwt, community_ids_cache, primary_community, cross_communities, title, url):
    """Create the canonical post in primary_community, then create posts with the same URL in cross_communities.

    Returns list of (community_name, success_bool, response) for attempted posts; the first entry is the primary post.
    """
    results = []

    # Resolve primary community id
    if primary_community not in community_ids_cache:
        try:
            community_ids_cache[primary_community] = get_community_id(base_url, primary_community, jwt)
        except Exception as e:
            logging.error(f'Error getting community ID for "{primary_community}": {e}')
            results.append((primary_community, False, str(e)))
            return results

    primary_id = community_ids_cache[primary_community]

    # Create canonical post (regular link post)
    ok, resp = create_post(base_url, jwt, primary_id, primary_community, title, url)
    results.append((primary_community, ok, resp))
    if not ok:
        return results

    # Prepare crosspost list (avoid duplicating primary)
    communities_to_cross = []
    if cross_communities:
        for c in cross_communities:
            if not c:
                continue
            if c == primary_community:
                continue
            if c not in communities_to_cross:
                communities_to_cross.append(c)

    # For each cross target, resolve id and create a post with the same url (server will surface it as a cross_post)
    for target in communities_to_cross:
        try:
            if target not in community_ids_cache:
                try:
                    community_ids_cache[target] = get_community_id(base_url, target, jwt)
                except Exception as e:
                    logging.error(f'Error getting community ID for crosspost target "{target}": {e}')
                    results.append((target, False, str(e)))
                    continue

            target_id = community_ids_cache[target]
            ok, resp = create_post(base_url, jwt, target_id, target, title, url)
            results.append((target, ok, resp))
        except Exception as e:
            logging.error(f'Unexpected error while crossposting to {target}: {e}')
            logging.debug(traceback.format_exc())
            results.append((target, False, str(e)))

    return results


def main():
    # Show the marketing banner with style and colors
    show_banner()

    args = parse_args()

    if args.example:
        print("""
Examples of Lemmy RSS PyBot Usage:

1. Basic Usage:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --interval 15

2. Using Specific Time Interval:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --time 20

3. Post Simultaneously to Communities (2 posts each):
   python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --simultaneously 2 --interval 10

4. Verbose Mode:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --verbose

5. Keyword Filtering:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --keywords "technology, science" --max_posts 5

6. Keyword Filtering from File:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --keywords-file keywords.txt --max_posts 5
   
7. Keyword Filtering by using custom keywords:
   python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --keywords "Ελλάδα, Κύπρος, Europe, Israel, Ισραήλ, Οικονομία, Business" --max_posts 5 --interva[...]
""")
        sys.exit(0)

    setup_logging(args.log, args.verbose)

    # Clean old log entries before starting
    clean_old_logs(args.log)

    # Track the time for 48-hour cleanups
    last_cleanup_time = datetime.now()

    try:
        lemmy_username, lemmy_password, lemmy_instance_url = load_credentials()
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    try:
        feeds = load_feeds(args.feeds)
    except Exception as e:
        logging.error(f'Error loading feeds: {e}')
        sys.exit(1)

    # Load keywords
    keywords = load_keywords(args.keywords, args.keywords_file)

    if keywords:
        logging.info(f"Filtering articles with keywords: {', '.join(keywords)}")
    else:
        logging.info("No keywords specified. All articles will be considered.")

    seen_articles = load_seen_articles(args.log)

    jwt = None
    def login():
        nonlocal jwt
        try:
            jwt = lemmy_login(lemmy_instance_url, lemmy_username, lemmy_password)
        except Exception as e:
            logging.error(f'Error logging in to Lemmy: {e}')
            sys.exit(1)

    login()

    community_ids = {}
    last_post_time = {}
    feed_index = {}

    simultaneously = args.simultaneously if args.simultaneously else 1

    try:
        while True:
            # Clean up logs every 48 hours
            current_time = datetime.now()
            time_since_last_cleanup = current_time - last_cleanup_time
            if time_since_last_cleanup.total_seconds() >= 48 * 3600:
                clean_old_logs(args.log)
                last_cleanup_time = current_time

            start_time = datetime.now(timezone.utc)
            posts_made = 0
            community_feed_map = {}
            for feed in feeds:
                if not feed.get('enabled', True):  # Skip if 'enabled' is False
                    logging.info(f"Skipping feed: {feed['feed_url']} (disabled)")
                    continue
                community_name = feed['community']
                if community_name not in community_feed_map:
                    community_feed_map[community_name] = []
                community_feed_map[community_name].append(feed)

            for community_name, community_feeds in community_feed_map.items():
                if community_name not in community_ids:
                    try:
                        community_id = get_community_id(lemmy_instance_url, community_name, jwt)
                        community_ids[community_name] = community_id
                    except Exception as e:
                        logging.error(f'Error getting community ID for "{community_name}": {e}')
                        continue

                community_id = community_ids[community_name]

                if community_name not in feed_index:
                    feed_index[community_name] = random.randint(0, len(community_feeds) - 1)

                # Determine interval minutes (support args.interval and fallback to random)
                interval_arg = getattr(args, 'interval', None)
                interval_minutes = interval_arg if interval_arg is not None else random.randint(11, 23)

                if community_name not in last_post_time or \
                   (datetime.now(timezone.utc) - last_post_time[community_name]).total_seconds() > interval_minutes * 60:

                    simultaneous_posts = 0
                    current_feed_idx = feed_index[community_name]

                    feeds_checked = 0
                    feeds_to_check = len(community_feeds)
                    found_matching_articles = False

                    while feeds_checked < feeds_to_check and simultaneous_posts < simultaneously and posts_made < args.max_posts:
                        selected_feed = community_feeds[current_feed_idx]
                        feed_url = selected_feed['feed_url']

                        try:
                            feed_data = fetch_feed_with_retries(feed_url)  # Using retry logic
                        except Exception as e:
                            logging.error(f"Failed to fetch feed {feed_url}: {e}")
                            # Move to next feed
                            current_feed_idx = (current_feed_idx + 1) % len(community_feeds)
                            feed_index[community_name] = current_feed_idx
                            feeds_checked += 1
                            continue  # Proceed to next feed

                        for entry in feed_data.entries:
                            article_title = entry.get('title', '')
                            link = entry.get('link', '')

                            # Initialize content_to_search as an empty string
                            content_to_search = ""

                            if not article_title or not link:
                                continue  # Skip if essential data is missing

                            # Skip if this article was already posted to this community
                            if link in seen_articles and ('*' in seen_articles[link] or community_name in seen_articles[link]):
                                continue

                            # Per-feed include_regex filter: if provided, match it against the URL path.
                            include_regex = selected_feed.get('include_regex')
                            if include_regex and link:
                                try:
                                    from urllib.parse import urlparse
                                    parsed = urlparse(link)
                                    path = parsed.path or ""
                                    pattern = regex.compile(include_regex, flags=regex.IGNORECASE)
                                    if not pattern.search(path):
                                        logging.debug(f"Skipping article '{article_title}' because URL path '{path}' does not match include_regex '{include_regex}'.")
                                        continue
                                except Exception as e:
                                    logging.debug(f"Error applying include_regex '{include_regex}' to link '{link}': {e}")

                            # Build the content to search for keywords
                            if keywords:
                                content_to_search = f"{article_title} {entry.get('summary', '')}"
                                content_to_search = unicodedata.normalize('NFKD', content_to_search)
                                content_to_search = unicodedata.normalize('NFC', content_to_search)

                            # Skip articles if keyword filtering is enabled and no keywords are matched
                            if keywords and content_to_search:
                                keywords_normalized = [unicodedata.normalize('NFC', kw) for kw in keywords]
                                matched = False
                                for keyword in keywords_normalized:
                                    pattern = regex.compile(r'\b' + regex.escape(keyword) + r'\b', flags=regex.IGNORECASE | regex.UNICODE)
                                    if pattern.search(content_to_search):
                                        matched = True
                                        logging.debug(f"Article '{article_title}' matched keyword '{keyword}'.")
                                        break
                                if not matched:
                                    logging.debug(f"Skipping article '{article_title}' as it does not match any keyword.")
                                    continue  # Skip if none of the keywords are found

                            # Proceed to post the article (create canonical post then create posts with same URL for native crossposts)
                            crosspost_list = selected_feed.get('crosspost') or selected_feed.get('crosspost_communities')
                            # Accept either a list or a comma-separated string
                            if isinstance(crosspost_list, str):
                                crosspost_list = [c.strip() for c in crosspost_list.split(',') if c.strip()]

                            results = post_article_primary_and_crossposts(lemmy_instance_url, jwt, community_ids, community_name, crosspost_list, article_title, link)

                            # Update seen_articles for successful posts (per-community)
                            any_success = False
                            for (comm, ok, resp) in results:
                                if ok:
                                    seen_articles.setdefault(link, set()).add(comm)
                                    any_success = True

                            if any_success:
                                # mark last post time for the primary community
                                last_post_time[community_name] = datetime.now(timezone.utc)
                                posts_made += 1
                                simultaneous_posts += 1
                                found_matching_articles = True

                                if simultaneous_posts >= simultaneously or posts_made >= args.max_posts:
                                    break

                        # Move to next feed
                        current_feed_idx = (current_feed_idx + 1) % len(community_feeds)
                        feed_index[community_name] = current_feed_idx
                        feeds_checked += 1

                        if simultaneous_posts >= simultaneously or posts_made >= args.max_posts:
                            break

                    if not found_matching_articles:
                        logging.info(f"No matching articles found for community '{community_name}'.")

            if posts_made == 0:
                interval = interval_minutes if 'interval_minutes' in locals() else random.randint(11, 23)
                logging.info(f"No new posts made. Sleeping for {interval} minutes.")
                time.sleep(interval * 60)
            else:
                elapsed_time = datetime.now(timezone.utc) - start_time
                sleep_time = (interval_minutes if 'interval_minutes' in locals() else random.randint(11, 23)) * 60 - elapsed_time.total_seconds()
                if sleep_time > 0:
                    logging.info(f"Sleeping for {sleep_time / 60:.2f} minutes.")
                    time.sleep(sleep_time)
    except KeyboardInterrupt:
        logging.info('Finishing execution of the Bot!')
        sys.exit(0)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
