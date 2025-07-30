import subprocess
import webbrowser
import time
import sys

def main():
    print("🎮 Starting StringZ Translation Tool...")
    print("⏳ Please wait while the server starts...")
    
    try:
        # Start streamlit server
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
            '--server.port', '8501',
            '--server.headless', 'true'
        ])
        
        # Wait for server to start
        time.sleep(4)
        
        # Open browser
        print("🌐 Opening browser...")
        webbrowser.open('http://localhost:8501')
        
        print("✅ StringZ is now running!")
        print("🔴 Close this window to stop the tool")
        
        # Keep the process running
        process.wait()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to close...")

if __name__ == "__main__":
    main()
