import subprocess
import webbrowser
import time
import sys
import os

def main():
    print("Starting StringZ Translation Tool...")
    
    # Get the directory where the executable is located
    if getattr(sys, 'frozen', False):
        # Running as executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    streamlit_app_path = os.path.join(app_dir, 'streamlit_app.py')
    
    try:
        # Start streamlit
        print("📂 Starting server...")
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', streamlit_app_path,
            '--server.port', '8501',
            '--server.headless', 'true',
            '--server.address', 'localhost'
        ])
        
        # Wait for server to start
        time.sleep(3)
        
        # Open browser
        print("🌐 Opening browser...")
        webbrowser.open('http://localhost:8501')
        
        print("✅ StringZ is running at http://localhost:8501")
        print("❌ Close this window to stop the tool")
        
        # Keep running
        process.wait()
        
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")

if __name__ == "__main__":
    main()
