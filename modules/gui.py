import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import praw
from . import reddit_listener


class App:
    """
    Tkinter GUI application for monitoring Reddit activity in a background thread
    and displaying messages in a scrollable log window.
    """
    def __init__(self, root):
        """
        Initialize the GUI, create widgets, set the initial state, and start the
        polling of the message queue (thread-safe).

        Args:
            root (tk.Tk): The Tkinter root window that owns this application.
        """
        # Main window.
        self.root = root
        self.root.title("Reddit Listener")

        # Create and pack a scrollable text widget to display log, wraps text.
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=80, height=20)
        self.log_area.pack(padx=10, pady=10)

        # Create and pack a start monitoring button.
        self.start_button = tk.Button(root, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=5)

        # Create and pack a stop monitoring button.
        self.stop_button = tk.Button(root, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=10, pady=5)

        self.message_queue = queue.Queue()
        self.check_queue()  
        self.running = False
        self.monitor_thread = None

    def start_monitoring(self):
        """
        Begin monitoring Reddit in a daemon thread, update button
        states accordingly, and log the action.
        """
        self.running = True 
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.monitor_thread = threading.Thread(
            target=self.reddit_monitor_worker,
            daemon=True) # Thread will automatically terminate when the main program closes.
        self.monitor_thread.start()


    def stop_monitoring(self):
        """
        Signal the background worker to stop, restore button states, and log
        the action. The worker loop observes 'self.running' and exits.
        """
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log("Stopping Reddit monitor.\n")

    def log(self, message):
        """
        Append a message to the scrollable log area and auto-scroll to the end.

        Args:
            message (str): Text to display in the log.
        """
        self.log_area.insert(tk.END, message)
        self.log_area.see(tk.END)

    def check_queue(self):
        """
        Empties the thread-safe message queue and writes them to the log.
        """
        try:
            while True:
                message = self.message_queue.get_nowait() # non-blocking to allow GUI updates
                self.log(message)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue) # Ensure check_queue doesn't hog the main thread.

    def reddit_monitor_worker(self):
        """
        Background worker: initializes the Reddit client, streams new submissions
        and comments from specified subreddits, formats summaries, and posts
        messages to the GUI queue until 'self.running' becomes False.
        """
        try:
            self.message_queue.put("Starting Reddit monitor.\n")
            reddit_instance = reddit_listener.initialize_reddit()
            self.message_queue.put("Connection successful.\n")

            monitored_subreddits = ["smallbusiness", "learnpython"]

            for item in reddit_listener.stream_reddit_activity(reddit_instance, monitored_subreddits):
                if not self.running:
                    break

                if isinstance(item, praw.models.Submission):
                    msg = (
                        f"New Post in r/{item.subreddit.display_name}:\n"
                        f"  Title: {item.title}\n"
                        f"  URL: https://www.reddit.com{item.permalink}\n"
                    )
                elif isinstance(item, praw.models.Comment):
                    msg = (
                        f"New Comment in r/{item.subreddit.display_name}:\n"
                        f"  Comment: {item.body[:80]}...\n"
                        f"  URL: https://www.reddit.com{item.permalink}\n"
                    )
                else:
                    continue
                self.message_queue.put(msg)
        except Exception as e:
            self.message_queue.put(f"Error: {e}\n")
        finally:
            self.message_queue.put("Stopping Reddit monitor.\n")