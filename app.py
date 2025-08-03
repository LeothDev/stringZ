import sys
import time
import os
import logging

from app import create_app

logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

app = create_app()
       
if __name__ == '__main__':
    import webbrowser
    import threading
    import time

    browser_opened = False
    
    def open_browser():
        """Open browser after a short delay to ensure server is running"""
        global browser_opened
        if not browser_opened:
            time.sleep(5)  # Wait for Flask to start
            webbrowser.open('http://127.0.0.1:5000')
            browser_opened = True
    
    # Start browser opening in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("StringZ is starting...")
    print("Translation QA Tool")
    print("Opening browser automatically...")
    print("If browser doesn't open, visit: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
