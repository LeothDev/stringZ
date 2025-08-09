from flask import Blueprint, session, flash, redirect, url_for, send_file
import pandas as pd
import os
import io
import time
import re

download_bp = Blueprint('download', __name__, url_prefix='/download')

@download_bp.route('/visualizer')
def download_visualizer():
    """Download the HTML Visualizer"""
    try:
        from stringZ.models.data_models import TranslationDataset
        from stringZ.export.visualizer import generate_visualizer_html

        # Use stored processedfile to recreate dataset
        processed_file = session.get('processed_file')
        if not processed_file  or not os.path.exists(processed_file):
            flash('No processed data found. Please process file first.', 'error')
            return redirect(url_for('main.results'))

        # Load processed dataframe
        df_processed = pd.read_pickle(processed_file)
        
        # Session info to properly recreate the dataset as DataFrame
        source_col = session.get('source_col')
        target_language = session.get('target_language')
        str_id_col = session.get('str_id_col')
        print(str_id_col)

        # Check if we need to rename the column
        if str_id_col in df_processed.columns:
            # Column already has correct name
            pass
        elif 'strId' in df_processed.columns and str_id_col != 'strId':
            # Rename strId back to original name
            df_processed = df_processed.rename(columns={'strId': str_id_col})
            print(f"DEBUG - Renamed 'strId' back to '{str_id_col}'")

        print(f"DEBUG - Final DataFrame columns: {df_processed.columns.tolist()}")

        print(f"DEBUG - About to create dataset with columns:")
        print(f"  str_id_col: {str_id_col}")
        print(f"  source_col: {source_col}")  
        print(f"  target_language: {target_language}")
        print(f"  DataFrame columns: {df_processed.columns.tolist()}")

        # Finally create the dataset
        processed_dataset = TranslationDataset.from_dataframe(
            df_processed,
            source_col=source_col,
            target_col=target_language,
            str_id_col=str_id_col
        )

        # Generate the Visualizer through the template
        original_filename = session.get('original_filename', 'processed')
        visualizer_html = generate_visualizer_html(processed_dataset, original_filename)

        # Create clean filename
        if original_filename:
            clean_name = re.sub(r'\.[^.]+$', '', original_filename)
            filename = f"Visualizer-{clean_name}.html"
        else:
            current_time = int(time.time())
            filename = f"Visualizer-{target_language}-{current_time}.html"

        # Create the final file object 
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
        flash(f"Error generating visualizer: {str(e)}", "error")
        return redirect(url_for('main.results'))

@download_bp.route('/spreadsheet')
def download_spreadsheet():
    """Download the processed Excel spreadsheet"""
    try:
        # Use stored processed file from the current session
        processed_file = session.get('processed_file')
        if not processed_file or not os.path.exists(processed_file):
            flash('No processed data found. Please process file first.', "error")
            return redirect(url_for("main.results"))

        df_processed = pd.read_pickle(processed_file)

        # Create the Excel file object
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_processed.to_excel(writer, sheet_name="Processed_Translations", index=False) 
        output.seek(0)

        original_filename = session.get('original_filename', 'processed')
        filename = f"{original_filename}_Processed.xlsx"

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        flash(f"Error generating spreadsheet: {str(e)}", "error")
        return redirect(url_for("main.results"))
