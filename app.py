import sys
import time
import os
import logging

from app import create_app

logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

app = create_app()

def open_browser():
    """Open browser after a short delay so that the server has time to get going"""
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:5000")
       
if __name__ == '__main__':
    import webbrowser
    import threading
    
    if not os.environ.get('DOCKER_CONTAINER'):
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            threading.Thread(target=open_browser, daemon=True).start()
    
    print("StringZ is starting...")
    print("Translation QA Tool")

    if os.environ.get('DOCKER_CONTAINER'):
        print("Running in Docker container")
        print("Visit: http://localhost:5000")
    else:
        print("Opening browser automatically...")
        print("If browser doesn't open, visit: http://127.0.0.1:5000")

    print("Press Ctrl+C to stop")

    host = '0.0.0.0' if os.environ.get('DOCKER_CONTAINER') else '127.0.0.1'
    
    app.run(debug=True, host=host, port=5000, threaded=True)
