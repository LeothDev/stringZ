import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, send_from_directory, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main page - show upload form or results based on the session"""
    if 'processed_dataset' in session:
        return render_template('pages/results.html')
    else:
        return render_template('pages/upload.html')

@main_bp.route('/test')
def test():
    return jsonify({
                       'status':'server is alive'
                   })

@main_bp.route('/results')
def results():
    """Show processing results and download options"""
    if 'processed_dataset' not in session:
        flash('No processed dataset found. Please upload and process a file')
        return redirect(url_for('main.index'))

    return render_template('pages/results.html')

@main_bp.route('/reset')
def reset_session():
    """Clear the current session and start over"""
    
        # Clean up temp files
    if 'temp_file' in session:
        temp_file = session['temp_file']
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    session.clear()
    flash('Session cleared. You can now upload a new file.', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/favicon.ico')
def favicon():
    """Simply serve the favicon of the app"""
    return send_from_directory('static', 'favicon.ico')

