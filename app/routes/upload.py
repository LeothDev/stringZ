from flask import Blueprint, request, session, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename

from app.services.file_services import FileService

upload_bp = Blueprint('upload', __name__)
    
@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    print("=== FLASK UPLOAD ROUTE HIT ===")
    print(f"Request method: {request.method}")
    print(f"Files in request: {list(request.files.keys())}")
    
    from flask import current_app
    
    if 'file' not in request.files:
        print("ERROR: No file in request")
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    print(f"File received: {file.filename}, size: {file.content_length}")
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not FileService.allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({'error': 'Invalid file type. Please upload .xlsx or .xls files'}), 400
    
    try:
        # Read the uploaded Excel file
        df = pd.read_excel(file)
        
        # Store original filename
        session['original_filename'] = secure_filename(file.filename)
        
        # Detect columns
        str_id_col, source_col, detected_source_lang = FileService.detect_columns(df)
        
        if not str_id_col:
            return jsonify({'error': 'No string ID column found! Expected one of: KEY_NAME, strId, ID, strID, 字符串'}), 400
        
        if not source_col:
            return jsonify({'error': 'No English source column found! Expected one of: EN, English, Source'}), 400

        print(f"DEBUG: Detected - str_id: {str_id_col}, source: {source_col}, lang: {detected_source_lang}")
        session['detected_source_lang'] = detected_source_lang

        excluded_columns = [str_id_col, source_col, "max", "Status"]
        if detected_source_lang == "CN" and 'EN' in df.columns:
            excluded_columns.append('EN')
        # Find target language columns
        lang_columns = [col for col in df.columns if col not in excluded_columns]
        print(f"DEBUG: Target language columns: {lang_columns}")
        
        if not lang_columns:
            return jsonify({'error': f'No target language columns found! Make sure your file has columns other than {str_id_col} and {source_col}'}), 400
        
        # Store the dataframe and column info in session (temporarily)
        session['df_columns'] = df.columns.tolist()
        session['str_id_col'] = str_id_col
        session['source_col'] = source_col
        session['lang_columns'] = lang_columns
        
        # Save the dataframe temporarily  
        temp_file = FileService.save_temp_file(df, id(session), current_app.config['UPLOAD_FOLDER'])
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

@upload_bp.route('/load_data', methods=['POST'])
def load_data():
    """Load data with selected target language and show preview"""
    try:
        from stringZ.models.data_models import TranslationDataset

        target_language = request.json.get('targetLanguage')
        if not target_language:
            return jsonify({'error': 'No target language selected'}), 400
        print(f"DEBUG: Selected target language: {target_language}")
        
        # Load the temporary dataframe
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'No uploaded file found. Please upload again.'}), 400
        
        df = FileService.load_temp_file(temp_file)
        print(f"DEBUG: Loaded DataFrame columns: {df.columns.tolist()}")
        
        # Get column info from session
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        detected_source_lang = session.get('detected_source_lang', 'EN')
        
        print(f"DEBUG: Session data - str_id: {str_id_col}, source: {source_col}, detected_lang: {detected_source_lang}")

        # Determine which columns to keep
        is_chinese_target = target_language in ['CNTraditional', 'CNSimplified']
        has_en_column = 'EN' in df.columns.tolist()
        source_is_chinese = detected_source_lang == 'CN' or source_col in ['base', 'CN']

        print("DEBUG: Chinese mode checks:")
        print(f"  - is_chinese_target: {is_chinese_target}")
        print(f"  - has_en_column: {has_en_column}")
        print(f"  - source_is_chinese: {source_is_chinese}")
        
        if is_chinese_target and has_en_column and source_is_chinese:
            columns_to_keep = [str_id_col, source_col, 'EN', target_language]
            print(f"DEBUG: Chinese mode detected - columns: {columns_to_keep}")
        else:
            columns_to_keep = [str_id_col, source_col, target_language]
            print(f"DEBUG: Normal mode - columns: {columns_to_keep}")
        
        # Validate columns exist
        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            return jsonify({'error': f'Missing columns: {", ".join(missing_cols)}'}), 400
        
        df_filtered = df[columns_to_keep].copy()
        print(f"DEBUG: Filtered DataFrame shape: {df_filtered.shape}")
        print(f"DEBUG: Filtered DataFrame columns: {df_filtered.columns.tolist()}")

        actual_source_col = source_col
        if 'base' in df_filtered.columns:
            df_filtered = df_filtered.rename(columns={'base': 'CN'})
            if source_col == 'base':
                actual_source_col = 'CN'

        # Check for None values before creating dataset
        for col in df_filtered.columns:
            none_count = df_filtered[col].isnull().sum()
            if none_count > 0:
                print(f"DEBUG: Column '{col}' has {none_count} null values")        


        df_filtered = df_filtered.fillna('')
        # Create TranslationDataset
        dataset = TranslationDataset.from_dataframe(
            df_filtered,
            source_col=actual_source_col,
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
        
        # Get preview data for a quick glance at the spreadsheet (first 10 rows)
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


@upload_bp.route('/process', methods=['POST'])
def process_file():
    """Process the loaded dataset with selected options"""
    from flask import current_app
    try:
        from stringZ.models.data_models import TranslationDataset
        from stringZ.core.processor import TranslationProcessor, ProcessingConfig
        
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
        
        df = FileService.load_temp_file(temp_file)
        
        # Get stored info
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        # target_language = request.json.get('targetLanguage')
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
        
        processed_df = processed_dataset.to_dataframe()
        print(f"DEBUG - After to_dataframe(), columns: {processed_df.columns.tolist()}")
        print(f"DEBUG - Dataset str_id_col: {processed_dataset.str_id_col}")
        processed_file = os.path.join(current_app.config['UPLOAD_FOLDER'], f"processed_{id(session)}.pkl")
        processed_df.to_pickle(processed_file)
        
        # Store everything in session
        session['processed_dataset'] = processed_dataset
        session['processed_file'] = processed_file 
        session['processing_stats'] = processor.get_processing_stats(processed_dataset)
        
        # Calculate final stats for metrics
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

