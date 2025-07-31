import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.ui.config.app_config import initialize_app 
from stringZ.ui.layouts.main_layout import render_main_layout

def main():   
    initialize_app()
    render_main_layout()

if __name__ == "__main__":
    main()
