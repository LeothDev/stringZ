import pandas as pd
import os

class FileService:
    @staticmethod
    def allowed_file(filename, allowed_extensions):
        """Check if files extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    @staticmethod
    def detect_columns(df):
        """Detect string ID, source column and Supplementary LANG, return both"""
        # String ID column detection
        str_id_names = ['strId', 'ID', 'strID', '字符串', 'id', 'StringID', 'string_id', 'KEY_NAME', "SOURCE"]
        str_id_col = None
        for col in df.columns:
            if col in str_id_names:
                str_id_col = col
                print(f"DEBUG: Found string ID column: {str_id_col}")
                break

        # If no named column is found check for empty header
        if  str_id_col is None:
            for col in df.columns:
                if col.startswith('Unnamed:'):
                    df.rename(columns={col: 'strId'}, inplace=True)
                    str_id_col = 'strId'
                    break

        source_col = None
        detected_supplementary_lang = None

        chinese_patterns = ['base', 'CN', 'Chinese', 'zh', 'ZH', 'chinese']
        for col in df.columns:
            if col in chinese_patterns:
                source_col = col
                detected_source_lang = 'CN'
                print(f"DEBUG: Found Chinese source column: {source_col}")
                break

        if source_col is None:
            english_patterns = ['EN', 'English', 'Source', 'en', 'english', 'source']
            for col in df.columns:
                if col in english_patterns:
                    source_col = col
                    detected_source_lang = 'EN'
                    print(f"DEBUG: Found English source column: {source_col}")
                    break

        print(f"DEBUG: Final detection - str_id: {str_id_col}, source: {source_col}, lang: {detected_source_lang}")
        return str_id_col, source_col, detected_source_lang

    @staticmethod
    def save_temp_file(df, session_id, upload_folder):
        """Save dataframe temporarily and return file path"""
        temp_file = os.path.join(upload_folder, f"temp_{session_id}.pkl")
        df.to_pickle(temp_file)
        return temp_file

    @staticmethod
    def load_temp_file(temp_file_path):
        """Load dataframe from temporary file"""
        if not temp_file_path or not os.path.exists(temp_file_path):
            return None
        return pd.read_pickle(temp_file_path)
