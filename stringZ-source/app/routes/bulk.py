from flask import Blueprint, render_template, request, session, jsonify, send_file
import pandas as pd
import os
import io
import zipfile
import re
from werkzeug.utils import secure_filename

from app.services.file_services import FileService

bulk_bp = Blueprint('bulk', __name__, url_prefix='/bulk')

@bulk_bp.route('/')
def bulk_index():
    """Bulk visualizer generation page"""
    return render_template('pages/bulk.html')

@bulk_bp.route('/upload', methods=['POST'])
def bulk_upload():
    """Handle file upload and detect ALL language columns"""
    from flask import current_app

    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Invalid file type. Please upload .xlsx .xls files'}), 400

    try:
        # Read uploaded Excel
        df = pd.read_excel(file)


        str_id_col, source_col = FileService.detect_columns(df)
        if not str_id_col:
            return jsonify({'error': 'No string ID column found! Expected one of KEY_NAME, strId, strID, 字符串, etc'}), 400

        if not source_col:
            return jsonify({'error': 'No English source column found! Expected one of: EN, English, Source'}), 400

        # Find ALL target language columns (except strId, EN, max, Status)
        target_lang_columns = [col for col in df.columns if col not in [str_id_col, source_col, "max", "Status"]]
        if not target_lang_columns:
            return jsonify({'error': f'No target language columns found! Make sure your file has language columns other than {str_id_col} and {source_col}'}), 400

        # Store bulk session data
        session['bulk_original_filename'] = secure_filename(file.filename)
        session['bulk_str_id_col'] = str_id_col
        session['bulk_source_col'] = source_col
        session['bulk_target_languages'] = target_lang_columns

        temp_file = FileService.save_temp_file(df, f"bulk_{id(session)}", current_app.config['UPLOAD_FOLDER'])
        session['bulk_temp_file'] = temp_file

        return jsonify({
                       'success': True,
                       'str_id_col': str_id_col,
                       'source_col': source_col,
                       'target_languages': target_lang_columns,
                       'total_entries': len(df),
                       'languages_count': len(target_lang_columns)
                       })
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 400

@bulk_bp.route('/generate', methods=['POST'])
def bulk_generate():
    """Generate visualizers for all selected languages and return as ZIP"""
    try:
        from stringZ.models.data_models import TranslationDataset
        from stringZ.export.visualizer import generate_bulk_visualizer_html

        # Get the languages
        data = request.json
        selected_languages = data.get('selectedLanguages', [])
        if not selected_languages:
            return jsonify({'error': 'No languages selected for generation'}), 400

        temp_file = session.get('bulk_temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'No uploaded file found. Please upload again.'}), 400

        df = FileService.load_temp_file(temp_file)

        str_id_col = session.get('bulk_str_id_col')
        source_col = session.get('bulk_source_col')
        original_filename = session.get('bulk_original_filename', 'bulk_visualizers')

        # ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for target_lang in selected_languages:
                # NO DEDUPLICATION OR CLUSTERING
                columns_to_keep = [str_id_col, source_col, target_lang]
                df_lang = df[columns_to_keep].copy()

                dataset = TranslationDataset.from_dataframe(
                    df_lang,
                    source_col=source_col,
                    target_col=target_lang,
                    str_id_col=str_id_col
                )

                # Generate Visualizers without occurrences column
                visualizer_html = generate_bulk_visualizer_html(dataset, original_filename)
                viz_filename = f"Visualizer-{target_lang}.html"

                zip_file.writestr(viz_filename, visualizer_html.encode('utf-8'))

        zip_buffer.seek(0)    

        clean_name = re.sub(r'\.[^.]+$', '', original_filename)
        zip_filename = f"{clean_name}-Visualizers.zip"

        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype="application/zip"
        )
    except Exception as e:
        return jsonify({'error': f'Bulk generation failed: {str(e)}'}), 400
    
