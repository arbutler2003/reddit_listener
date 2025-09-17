Reddit_listener is a Python based automation tool that monitors local subreddits for relevant keywords. When a match is discovered in a post/comment, a alert is dispatched via (TBD).

Features
- Reddit Feed Monitoring: Uses Reddit's API stream.
- Keyword Matching: Scans Reddit's stream for specified keywords.
- Notification: Sends alerts via email when a post/comment matches specified keywords.
- Duplicate Prevention: Tracks previously handled post/comments to prevent sending duplicate alerts.

Language: Python 3.9
Libraries:
- praw: Python Reddit API wrapper.
- python-dotenv: Managing environment variables and secrets.
