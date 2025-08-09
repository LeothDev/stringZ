import os
import html
import pandas as pd
from flask import Blueprint, request, session, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/page_data')
def get_page_data():
    """API endpoint to get page data for results"""
    if 'processed_dataset' not in session or 'processing_stats' not in session:
        return jsonify({'error': 'No processed data found'}), 400
    
    try:
        # Get the processed dataset stored in the current session
        temp_file = session.get('temp_file')
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({'error': 'Original data not found'}), 400
            
        # Get basic info from session
        stats = session['processing_stats']['processing_summary']
        target_language = session.get('target_language')
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        
        # Calculate completion rate (Indicates whether all the rows were processed)
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
                'completion_rate': f"{completion_rate:.1f}%",
                'original_filename': session.get('original_filename', 'Unknown')
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Error loading page data: {str(e)}'}), 400

@api_bp.route('/review_data')
def get_review_data():
    """API endpoint to review data for the table"""
    try:       
        # Use the stored processed dataframe directly
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            print("ERROR: No processed file found")
            return jsonify({'error': 'No processed data found. Please process file first.'}), 400
        
        # Load the EXACT same processed dataframe used for downloads
        df_display = pd.read_pickle(processed_file)

        # Get language info from session
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        str_id_col = session.get('str_id_col')
        
        # Get search and filter parameters
        search = request.args.get('search', '').strip()
        filter_type = request.args.get('filter', 'all')
        
        # Apply filtering
        filtered_df = df_display.copy()
        
        # Search filter
        if search:
            mask = filtered_df.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]
        
        # Type filters
        if filter_type == 'missing' and target_language in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[target_language].isna()]
        elif filter_type == 'priority' and 'Occurrences' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Occurrences'] > 5]
        
        # Get first 100 rows for display
        display_df = filtered_df.head(100)
        
        # Convert to records
        records = []
        for _, row in display_df.iterrows():
            occurrences_val = row.get('Occurrences', 1)
            if pd.isna(occurrences_val):
                occurrences_val = 1
            
            record = {
                'strId': str(row.get(str_id_col, '')),
                'source': str(row.get(source_col, '')),
                'target': str(row.get(target_language, '') if target_language in row else ''),
                'occurrences': int(occurrences_val)
            }
            records.append(record)
        
        # Calculate metrics
        missing_count = 0
        high_priority_count = 0
        
        if target_language in filtered_df.columns:
            missing_count = int(filtered_df[target_language].isna().sum())
        
        if 'Occurrences' in filtered_df.columns:
            high_priority_count = int((filtered_df['Occurrences'] > 5).sum())
        
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


@api_bp.route('/run_validation', methods=['POST'])
def run_validations():
    """API endpoint to run LQA Validation"""
    try:       
        from stringZ.models.data_models import TranslationDataset
        from stringZ.validation.validators import run_validation
       
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            return jsonify({'error': 'No processed data found to validate'}), 400

        df_processed = pd.read_pickle(processed_file)
        print(f"DEBUG: Loaded processed DataFrame with {len(df_processed)} rows")
       
        # Get stored session info
        str_id_col = session.get('str_id_col')
        source_col = session.get('source_col')
        target_language = session.get('target_language')

        if str_id_col in df_processed.columns:
            pass
        elif 'strId' in df_processed.columns and str_id_col != 'strId':
            df_processed = df_processed.rename(columns={'strId': str_id_col})
        
        # Create dataset from the PROCESSED dataframe
        processed_dataset = TranslationDataset.from_dataframe(
            df_processed,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )


        # Run validation directly on the processed dataset
        validation_results = run_validation(processed_dataset)
        
        # Format results for frontend
        formatted_issues = []
        for issue in validation_results['detailed_issues']:
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

