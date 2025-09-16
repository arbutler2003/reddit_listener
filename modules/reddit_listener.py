"""
This is the Reddit listener module.

This module connects to the Reddit API using PRAW for listening to Reddit posts and
comments from specified subreddits.
"""

import os  # For environment variable management.
import time  # For the 'sleep' function to pause the script during reconnection.
import logging  # Used for structured logging.
import praw  # Python Reddit API Wrapper (PRAW).
import prawcore  # Used for specific exception handling.
from dotenv import load_dotenv  # Load secrets from a local .env file.


# Creates a logger named after the module.
logger = logging.getLogger(__name__)
# Ensures that the logger is configured only once.
if not logger.handlers:
    logging.basicConfig(
        # INFO level and above (Warning, Error, Critical)
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

def initialize_reddit():
    """
    Initializes the Reddit instance using PRAW.
    Loads API credentials from .env and throws an exception if credentials are missing.

    Raises:
        ValueError: When any required environment variables are missing.
        RuntimeError: When credentials/network prevent successful authentication.
    Returns:
        praw.Reddit: An authenticated Reddit client.
    """
    # Load environment variables from .env into process environment.
    load_dotenv()

    required_env_vars = [
        'REDDIT_CLIENT_ID',
        'REDDIT_CLIENT_SECRET',
        'REDDIT_USER_AGENT',
        'REDDIT_USERNAME',
        'REDDIT_PASSWORD',
    ]

    logger.info('Authenticating with Reddit...')

    # Construct the PRAW client.
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT'),
        username=os.getenv('REDDIT_USERNAME'),
        password=os.getenv('REDDIT_PASSWORD'),
    )

    # Validate credentials.
    try:
        me = reddit.user.me()
        logger.info(f'Authentication successful. Logged in as {me}')
    except (
        prawcore.exceptions.OAuthException,
        prawcore.exceptions.InvalidToken,
        prawcore.exceptions.Forbidden,
        prawcore.exceptions.BadRequest,
        prawcore.exceptions.ResponseException,
        prawcore.exceptions.RequestException,
        prawcore.exceptions.ServerError,
    ) as e:
        raise RuntimeError(f"Failed to verify Reddit authentication: {e}") from e
    return reddit


def stream_reddit_activity(reddit, sub_reddits):
    """
    Yields a combined stream of new submissions and comments from one or more subreddits.
    This function runs continuously and uses exponential backoff to handle transient errors.

    Args:
        reddit (praw.Reddit): An authenticated Reddit client.
        sub_reddits (list[str]): Subreddit names (without the 'r/' prefix).

    Yields:
        praw.models.Submission | praw.models.Comment: Next item from the monitored subreddits.
    """
    # Convert an array of subreddits to a string for PRAW.
    subreddit_string = '+'.join(subreddit.strip() for subreddit in sub_reddits)

    # Get an object representing the specified subreddits.
    subreddit = reddit.subreddit(subreddit_string)

    backoff_seconds = 5
    max_backoff_seconds = 120
    while True:
        try:
            logger.info(f'Starting stream from subreddits: {subreddit_string}')

            # Pause_after=0 yields None when no items are available, allowing the streams to alternate.
            submissions_stream = subreddit.stream.submissions(skip_existing=True, pause_after=0)
            comments_stream = subreddit.stream.comments(skip_existing=True, pause_after=0)

            # Reset backoff.
            backoff_seconds = 5

            # Yields new items from the streams continuously.
            while True:
                for submission in submissions_stream:
                    if submission is None:
                        break
                    yield submission

                for comment in comments_stream:
                    if comment is None:
                        break
                    yield comment

                # Prevent a tight loop.
                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Stream interrupted by user. Shutting down.")
            raise
        except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound) as e:
            # Likely invalid or private subreddits.
            logger.error(f'Access issue for subreddits "{subreddit_string}": {e}. Stopping stream.')
            raise
        except (prawcore.exceptions.OAuthException, prawcore.exceptions.InvalidToken) as e:
            # Likely invalid credentials.
            logger.error(f'Authentication error while streaming: {e}. Stopping stream.')
            raise
        except (
            prawcore.exceptions.RequestException,   # Network timeouts.
            prawcore.exceptions.ResponseException,  # Unexpected HTTP issues.
            prawcore.exceptions.ServerError,        # 5xx errors from Reddit's servers.
        ) as e:
            # Backoff for transient errors.
            logger.warning(f'Error streaming from Reddit: {e}')
            sleep_for = min(max_backoff_seconds, int(backoff_seconds * 1.5))
            logger.info(f'Reconnecting in {sleep_for} seconds...')
            time.sleep(sleep_for)
            backoff_seconds = min(max_backoff_seconds, sleep_for * 2)
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            logger.info('Reconnecting in 15 seconds...')
            time.sleep(15)


if __name__ == '__main__':
    logger.info('Running reddit_listener.py as a standalone script.')

    try:
        reddit_instance = initialize_reddit()

        # Example subreddits to monitor.
        test_subreddits = ['smallbusiness', 'learnpython']

        # Stream indefinitely and print a summary for each item.
        for item in stream_reddit_activity(reddit_instance, test_subreddits):
            if isinstance(item, praw.models.Submission):
                print('-' * 40)
                print(f'New Post in r/{item.subreddit.display_name}:')
                print(f'  Title: {item.title}')
                print(f'  URL: https://www.reddit.com{item.permalink}')
            elif isinstance(item, praw.models.Comment):
                print('-' * 40)
                print(f'New Comment in r/{item.subreddit.display_name}:')
                print(f'  Comment: {item.body[:80]}...')
                print(f'  URL: https://www.reddit.com{item.permalink}')
    except ValueError as e:
        logger.error(f'Configuration Error: {e}')
    except RuntimeError as e:
        # Authentication failures
        logger.error(str(e))
    except KeyboardInterrupt:
        logger.info("Shut down by user.")
    except Exception as e:
        logger.exception(f'An unexpected error occurred: {e}')
