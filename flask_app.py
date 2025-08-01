import sys
import html
import time
import io
import os
import re
import tempfile
from flask import Flask, render_template, request, session, jsonify, url_for, flash, redirect, send_file
import pandas as pd
from werkzeug.utils import secure_filename

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.models.data_models import TranslationDataset
from stringZ.core.processor import TranslationProcessor, ProcessingConfig
from stringZ.validation.validators import run_validation
from stringZ.export.visualizer import generate_visualizer_html

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page - show upload form or results based on session state"""
    if 'processed_dataset' in session:
        return render_template('results.html')
    else:
        return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and column detection"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload .xlsx or .xls files'}), 400
    
    try:
        # Read the uploaded Excel file
        df = pd.read_excel(file)
        
        # Store original filename
        session['original_filename'] = secure_filename(file.filename)
        
        # Detect columns
        str_id_col = detect_str_id_column(df)
        source_col = detect_source_column(df)
        
        if not str_id_col:
            return jsonify({'error': 'No string ID column found! Expected one of: KEY_NAME, strId, ID, strID, 字符串'}), 400
        
        if not source_col:
            return jsonify({'error': 'No English source column found! Expected one of: EN, English, Source'}), 400
        
        # Find target language columns
        lang_columns = [col for col in df.columns if col not in [str_id_col, source_col]]
        
        if not lang_columns:
            return jsonify({'error': f'No target language columns found! Make sure your file has columns other than {str_id_col} and {source_col}'}), 400
        
        # Store the dataframe and column info in session (temporarily)
        session['df_columns'] = df.columns.tolist()
        session['str_id_col'] = str_id_col
        session['source_col'] = source_col
        session['lang_columns'] = lang_columns
        
        # Save the dataframe temporarily  
        temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{id(session)}.pkl")
        df.to_pickle(temp_file)
        session['temp_file'] = temp_file
        
        return jsonify({
            'success': True,
            'str_id_col': str_id_col,
            'source_col': source_col,
            'lang_columns': lang_columns,
            'total_entries': len(df)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 400

@app.route('/load_data', methods=['POST'])
def load_data():
    """Load data with selected target language and show preview"""
    try:
        target_language = request.json.get('targetLanguage')
        if not target_language:
            return jsonify({'error': 'No target language selected'}), 400
        
        # Load the temporary dataframe
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'No uploaded file found. Please upload again.'}), 400
        
        df = pd.read_pickle(temp_file)
        
        # Get column info from session
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        
        # Create filtered dataframe with only needed columns
        columns_to_keep = [str_id_col, source_col, target_language]
        df_filtered = df[columns_to_keep].copy()
        
        # Create TranslationDataset
        dataset = TranslationDataset.from_dataframe(
            df_filtered,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )
        
        # Store dataset info in session
        session['dataset_loaded'] = True
        session['target_language'] = target_language
        session['total_entries'] = len(dataset)
        
        # Calculate some preview stats
        duplicates = len(dataset.get_duplicates())
        completion = dataset.get_completion_rate()
        avg_length = sum(len(entry.source_text) for entry in dataset.entries) / len(dataset.entries)
        
        # Get preview data (first 10 rows)
        preview_data = []
        for entry in dataset.entries[:10]:
            preview_data.append({
                'strId': entry.str_id,
                'source': entry.source_text,
                'target': entry.target_text or ''
            })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_entries': len(dataset),
                'duplicate_groups': duplicates,
                'completion_rate': f"{completion:.1f}%",
                'avg_length': f"{avg_length:.0f}"
            },
            'preview_data': preview_data,
            'source_lang': source_col,
            'target_lang': target_language
        })
        
    except Exception as e:
        return jsonify({'error': f'Error loading data: {str(e)}'}), 400    

@app.route('/process', methods=['POST'])
def process_file():
    """Process the loaded dataset with selected options"""
    try:
        # Get processing options from request
        data = request.json
        remove_duplicates = data.get('removeDuplicates', True)
        sort_by_correlation = data.get('sortByCorrelation', True)
        correlation_strategy = data.get('correlationStrategy', 'hybrid')
        similarity_threshold = float(data.get('similarityThreshold', 0.7))
        max_cluster_size = int(data.get('maxClusterSize', 15))
        min_substring_length = int(data.get('minSubstringLength', 5))
        
        # Load the temporary dataframe and recreate dataset
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'No uploaded file found. Please upload again.'}), 400
        
        df = pd.read_pickle(temp_file)
        
        # Get stored info
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        
        # Create filtered dataframe
        columns_to_keep = [str_id_col, source_col, target_language]
        df_filtered = df[columns_to_keep].copy()
        
        # Create dataset
        dataset = TranslationDataset.from_dataframe(
            df_filtered,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )
        
        # Create processing configuration
        config = ProcessingConfig(
            remove_duplicates=remove_duplicates,
            deduplication_strategy="keep_first_with_occurrences",
            sort_by_correlation=sort_by_correlation,
            correlation_strategy=correlation_strategy,
            similarity_threshold=similarity_threshold,
            max_cluster_size=max_cluster_size,
            min_substring_length=min_substring_length
        )
        
        # Process the dataset
        processor = TranslationProcessor(config)
        processed_dataset = processor.process(dataset)
        
        # NEW: Store the EXACT processed dataframe for consistent use
        processed_df = processed_dataset.to_dataframe()
        processed_file = os.path.join(app.config['UPLOAD_FOLDER'], f"processed_{id(session)}.pkl")
        processed_df.to_pickle(processed_file)
        
        # Store everything in session
        session['processed_dataset'] = processed_dataset
        session['processed_file'] = processed_file  # NEW: Store processed file path
        session['processing_stats'] = processor.get_processing_stats(processed_dataset)
        
        # Calculate final stats
        target_word_count = 0
        if target_language in processed_df.columns:
            target_word_count = processed_df[target_language].dropna().astype(str).apply(lambda x: len(x.split())).sum()
        
        stats = session['processing_stats']['processing_summary']
        
        return jsonify({
            'success': True,
            'stats': {
                'original_count': stats['original_count'],
                'final_count': stats['final_count'],
                'duplicates_removed': stats['duplicates_removed'],
                'clusters_created': stats['clusters_created'],
                'word_count': f"{target_word_count:,}",
                'processing_time': stats['processing_time']
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 400

@app.route('/results')
def results():
    """Show processing results and download options"""
    if 'processed_dataset' not in session:
        flash('No processed data found. Please upload and process a file first.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html')

@app.route('/reset')
def reset_session():
    """Clear session and start over"""
    # Clean up temp files
    if 'temp_file' in session:
        temp_file = session['temp_file']
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    session.clear()
    flash('Session cleared. You can now upload a new file.', 'info')
    return redirect(url_for('index'))

@app.route('/api/page_data')
def get_page_data():
    """API endpoint to get page data for results"""
    if 'processed_dataset' not in session or 'processing_stats' not in session:
        return jsonify({'error': 'No processed data found'}), 400
    
    try:
        # Get the processed dataset (we'll need to recreate it from session)
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'Original data not found'}), 400
            
        # Get basic info from session
        stats = session['processing_stats']['processing_summary']
        target_language = session.get('target_language')
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        
        # Calculate completion rate from processed dataset
        df = pd.read_pickle(temp_file)
        columns_to_keep = [str_id_col, source_col, target_language]
        df_filtered = df[columns_to_keep].copy()
        
        completion_rate = (df_filtered[target_language].notna().sum() / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'original_count': stats['original_count'],
                'final_count': stats['final_count'],
                'duplicates_removed': stats['duplicates_removed'],
                'clusters_created': stats['clusters_created']
            },
            'quick_stats': {
                'total_entries': stats['final_count'],
                'source_lang': source_col,
                'target_lang': target_language,
                'completion_rate': f"{completion_rate:.1f}%"
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error loading page data: {str(e)}'}), 400

@app.route('/download/visualizer')
def download_visualizer():
    """Download the HTML visualizer"""
    try:
        # NEW: Use the stored processed file to recreate dataset
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            flash('No processed data found. Please process file first.', 'error')
            return redirect(url_for('results'))
        
        # Load processed dataframe and convert back to dataset
        df_processed = pd.read_pickle(processed_file)
        
        # Get session info to recreate dataset
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        str_id_col = session.get('str_id_col')
        
        # Create dataset from processed dataframe
        processed_dataset = TranslationDataset.from_dataframe(
            df_processed,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )
        
        # Generate visualizer HTML
        original_filename = session.get('original_filename', 'processed')
        visualizer_html = generate_visualizer_html(processed_dataset, original_filename)
        
        # Create filename
        current_time = int(time.time())
        if original_filename:
            clean_name = re.sub(r'\.[^.]+$', '', original_filename)
            filename = f"Visualizer-{clean_name}.html"
        else:
            filename = f"StringZ-Visualizer-{target_language}-{current_time}.html"
        
        # Create file-like object
        output = io.BytesIO()
        output.write(visualizer_html.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/html'
        )
        
    except Exception as e:
        flash(f'Error generating visualizer: {str(e)}', 'error')
        return redirect(url_for('results'))

@app.route('/download/spreadsheet')
def download_spreadsheet():
    """Download the processed Excel spreadsheet"""
    try:
        # NEW: Use the stored processed file directly
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            flash('No processed data found. Please process file first.', 'error')
            return redirect(url_for('results'))
        
        # Load the exact same processed dataframe
        df_processed = pd.read_pickle(processed_file)
        
        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_processed.to_excel(writer, sheet_name='Processed_Translations', index=False)
        
        output.seek(0)
        
        # Create filename
        current_time = int(time.time())
        filename = f"StringZ-Processed-{current_time}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Error generating spreadsheet: {str(e)}', 'error')
        return redirect(url_for('results'))

@app.route('/api/review_data')
def get_review_data():
    """API endpoint to get review data for the table"""
    try:
        print("=== DEBUG: Starting get_review_data ===")
        
        # NEW: Use the stored processed dataframe directly
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            print("ERROR: No processed file found")
            return jsonify({'error': 'No processed data found. Please process file first.'}), 400
        
        # Load the EXACT same processed dataframe used for downloads
        df_display = pd.read_pickle(processed_file)
        print(f"DEBUG: Loaded processed dataframe with {len(df_display)} rows")
        print(f"DEBUG: Columns: {list(df_display.columns)}")
        
        # Get language info from session
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        
        # Get search and filter parameters
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')
        
        print(f"DEBUG: search='{search}', filter_type='{filter_type}'")
        
        # Apply filtering
        filtered_df = df_display.copy()
        
        # Search filter
        if search:
            mask = filtered_df.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]
            print(f"DEBUG: After search filter: {len(filtered_df)} rows")
        
        # Type filters
        if filter_type == 'missing' and target_language in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[target_language].isna()]
            print(f"DEBUG: After missing filter: {len(filtered_df)} rows")
        elif filter_type == 'priority' and 'Occurrences' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Occurrences'] > 5]
            print(f"DEBUG: After priority filter: {len(filtered_df)} rows")
        
        # Get first 100 rows for display
        display_df = filtered_df.head(100)
        print(f"DEBUG: Showing {len(display_df)} rows")
        
        # Convert to records
        records = []
        for _, row in display_df.iterrows():
            occurrences_val = row.get('Occurrences', 1)
            if pd.isna(occurrences_val):
                occurrences_val = 1
            
            record = {
                'strId': str(row.get('strId', '')),
                'source': str(row.get(source_col, '')),
                'target': str(row.get(target_language, '') if target_language in row else ''),
                'occurrences': int(occurrences_val)
            }
            records.append(record)
        
        # Calculate stats
        missing_count = 0
        high_priority_count = 0
        
        if target_language in filtered_df.columns:
            missing_count = int(filtered_df[target_language].isna().sum())
        
        if 'Occurrences' in filtered_df.columns:
            high_priority_count = int((filtered_df['Occurrences'] > 5).sum())
        
        print(f"DEBUG: Created {len(records)} records")
        
        return jsonify({
            'success': True,
            'data': records,
            'pagination': {
                'total_entries': int(len(filtered_df)),
                'showing': int(len(records))
            },
            'stats': {
                'total_strings': int(len(filtered_df)),
                'missing_translations': missing_count,
                'high_priority': high_priority_count
            },
            'columns': {
                'source_lang': source_col,
                'target_lang': target_language
            }
        })
        
    except Exception as e:
        print(f"ERROR in get_review_data: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return jsonify({'error': f'Error loading review data: {str(e)}'}), 400

@app.route('/api/run_validation', methods=['POST'])
def run_validation_api():
    """API endpoint to run LQA validation"""
    try:
        print("=== DEBUG: Starting validation ===")
        
        # Recreate the processed dataset (using the same logic as review)
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'No data found to validate'}), 400
        
        # Get stored session info
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        
        # Load and create dataset
        df = pd.read_pickle(temp_file)
        columns_to_keep = [str_id_col, source_col, target_language]
        df_filtered = df[columns_to_keep].copy()
        
        dataset = TranslationDataset.from_dataframe(
            df_filtered,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )
        
        # Simple processing for validation
        config = ProcessingConfig(
            remove_duplicates=True,
            deduplication_strategy="keep_first_with_occurrences",
            sort_by_correlation=False
        )
        
        processor = TranslationProcessor(config)
        processed_dataset = processor.process(dataset)
        
        print(f"DEBUG: Running validation on {len(processed_dataset)} entries")
        
        # Run validation
        validation_results = run_validation(processed_dataset)
        
        print(f"DEBUG: Validation found {validation_results['issues_found']} issues")
        
        # Format results for frontend
        formatted_issues = []
        for issue in validation_results['detailed_issues'][:20]:  # Limit to first 20 for display
            formatted_issues.append({
                'str_id': issue['str_id'],
                'type': issue['type'],
                'severity': issue['severity'],
                'detail': issue['detail'],
                'en_text': html.escape(issue['en_text'][:100] + '...' if len(issue['en_text']) > 100 else issue['en_text']),
                'target_text': html.escape(issue['target_text'][:100] + '...' if len(issue['target_text']) > 100 else issue['target_text']),
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_strings': validation_results['total_strings'],
                'issues_found': validation_results['issues_found'],
                'critical_issues': validation_results['critical_issues'],
                'warnings': validation_results['warnings']
            },
            'issues': formatted_issues,
            'target_lang': target_language
        })
        
    except Exception as e:
        print(f"ERROR in validation: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return jsonify({'error': f'Validation failed: {str(e)}'}), 400

def recreate_processed_dataset():
    """Helper function to recreate processed dataset from session data"""
    try:
        # Load the temporary dataframe
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return None
        
        df = pd.read_pickle(temp_file)
        
        # Get stored info
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        
        # Create filtered dataframe
        columns_to_keep = [str_id_col, source_col, target_language]
        df_filtered = df[columns_to_keep].copy()
        
        # Create dataset
        dataset = TranslationDataset.from_dataframe(
            df_filtered,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )
        
        # We need to reprocess to get the same results
        # Get the last processing config from session (we should store this)
        config = ProcessingConfig(
            remove_duplicates=True,
            deduplication_strategy="keep_first_with_occurrences",
            sort_by_correlation=True,
            correlation_strategy="hybrid"
        )
        
        processor = TranslationProcessor(config)
        processed_dataset = processor.process(dataset)
        
        return processed_dataset
        
    except Exception as e:
        print(f"Error recreating dataset: {str(e)}")
        return None

def detect_str_id_column(df):
    """Detect string ID column with flexible naming"""
    possible_names = ['strId', 'ID', 'strID', '字符串', 'id', 'StringID', 'string_id', 'KEY_NAME']
    for col in df.columns:
        if col in possible_names:
            return col
    return None

def detect_source_column(df):
    """Detect English source column with flexible naming"""
    possible_names = ['EN', 'English', 'Source', 'en', 'english', 'source']
    for col in df.columns:
        if col in possible_names:
            return col
    return None

if __name__ == '__main__':
    app.run(debug=True)
