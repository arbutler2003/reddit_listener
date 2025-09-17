import tkinter as tk
from modules.gui import App

def main():
    """
    Initializes and runs the Reddit Listener GUI app.
    """
    # Create the main window
    root = tk.Tk()
    # Create an App instance
    app = App(root)
    # Run the main loop
    root.mainloop()

if __name__ == '__main__':
    main()