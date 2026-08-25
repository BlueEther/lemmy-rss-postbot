# Lemmy RSS PyBot 🤖
![Lemmy RSS PyBot Logo](assets/logo.jpg)

*Bringing the latest news to your favourite Lemmy communities!*

[![License](https://img.shields.io/badge/license-AGPL-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)

## 🚀 Introduction

Lemmy RSS PyBot is a powerful Python bot that reads RSS feeds and posts new articles to your favorite Lemmy communities. Stay updated with the latest news, blogs, and articles time-efficiently! 🤓

## ✨ Features

- 📥 Reads RSS feeds from a JSON file with associated communities.
- 📝 Posts new articles to specified Lemmy communities.
- 🔍 Filters articles with per-feed keywords, optional URL-path regexes, or global fallback keywords.
- ⏰ Checks for new articles every specified interval.
- ⚙️ Uses configuration files for settings and credentials.
- 📑 Keeps a log of posted articles with rotating logs and auto-clearing mechanism.
- 🛠️ Supports command-line arguments for customization.
- 💡 Includes comprehensive error handling and logging.
  
![Execution Screenshot](assets/screen.jpg)
## 📦 Requirements

- Lemmy account credentials in the .env file,
- Access to Lemmy instance API,
- A json file with the desired RSS links and communites with a true label to enable them.

## 🛠️ Installation (both locally or in Docker container)

```bash
git clone https://github.com/BlueEther/lemmy-rss-postbot.git
cd lemmy-rss-postbot
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and add your Lemmy credentials. `.env` is ignored by Git:

```dotenv
LEMMY_USERNAME=your_lemmy_username
LEMMY_PASSWORD=your_lemmy_password
LEMMY_INSTANCE_URL=https://your.lemmy.instance.url
```

### RSS Feeds

Create a `rss_feeds.json` file to specify feeds, target communities, and filters:

```json
[
    {
        "feed_url": "https://newssite1.com/rss",
        "community": "news@lemmy.example2",
        "keywords": ["technology", "science", "AI"],
        "include_regex": "^/(technology|science)/",
        "enabled": true
    },
    {
        "feed_url": "https://anotherexample.com/feed",
        "community": "technology@lemmy.exampple1",
        "keywords": ["Python", "Machine Learning"],
        "enabled": false
    }
]
```

## 🏃‍♂️ Usage

### Running Locally

#### Install Requirements

```bash
pip install -r requirements.txt
```

```bash
python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --interval 15
```

#### Examples

1. **Basic Usage:**

    ```bash
    python lemmy-rss-pybot.py
    ```

2. **Using Specific Time Interval:**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --time 20
    ```

3. **Post Simultaneously to Communities (2 posts each):**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --simultaneously 2 --interval 10
    ```

4. **Verbose Mode:**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --verbose
    ```

5. **Keyword Filtering:**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --keywords "technology, Europe, science" --max_posts 5
    ```

6. **Keyword Filtering from File:**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --keywords-file keywords.txt --max_posts 5
    ```

7. **Keyword Filtering with Custom Keywords:**

    ```bash
    python lemmy-rss-pybot.py --feeds rss_feeds.json --log lemmy_bot.log --keywords "Python, AI, Machine Learning" --max_posts 5 --interval 15
    ```
8. **Show detailed instructions:**
    
    ```bash
    python lemmy-rss-pybot.py --help
    ```

### Feed filters

Each feed supports these optional filters:

- `keywords`: an array of keywords matched case-insensitively against the title and summary. Matching any keyword is sufficient, including short terms such as `AI`.
- `include_regex`: a regular expression matched against the article URL path, not its hostname or query string.

When both filters are present, an article must pass both. Invalid or empty filters stop the bot during startup rather than allowing unfiltered posts.

Per-feed `keywords` override global keywords for that feed. A feed without its own keywords falls back to `--keywords` or `--keywords-file`. With neither configured, that feed is not keyword-filtered.

Global keyword options remain available:

- Create a `keywords.txt` file with one keyword per line.
- Or specify keywords via the `--keywords` argument.

Validate the complete feed configuration without logging in or posting:

```bash
python lemmy-rss-pybot.py --feeds rss_feeds.json --test
```

#### Run with Docker Compose 🐳
Compose builds this fork locally so its filtering changes are included. After configuring `.env` and `rss_feeds.json`, run:

```bash
docker compose build
docker compose run --rm --entrypoint python lemmy-rss-pybot /app/lemmy-rss-pybot.py --feeds /app/rss_feeds.json --test
docker compose up -d
```

The supplied Compose configuration posts at most one article per 15-minute cycle. Increase `--max_posts` only after reviewing verbose logs and confirming the filters behave as expected.

## 🎯 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License

This project is licensed under the GNU Affero General Public License (AGPL) - see the [LICENSE](https://www.gnu.org/licenses/agpl-3.0.html) file for details.

---

## 🤝 Contributing
Contributions are welcome! Feel free to fork the repository and submit a pull request. If you encounter any issues, please open an issue on GitHub. 

---

## ⚠️ Troubleshooting
- **Environment Variables Not Loaded**: Ensure you have a valid `.env` file in the root directory.
- **Missing Dependencies**: Run `pip install -r requirements.txt` to make sure all required packages are installed.
- **Syntax Issues in the JSON file**: Check the example RSS feeds JSON file.
- If you encounter any issues, please check the logs for more details.
```bash
tail -f lemmy_bot.log
```


🚀 **Lemmy RSS PyBot** – Created by Dimitris Vagiakakos [@sv1sjp](https://sv1sjp.github.io/whoami) - TuxHouse
