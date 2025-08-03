import pandas as pd
import os

class FileService:
    @staticmethod
    def allowed_file(filename, allowed_extensions):
        """Check if files extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    @staticmethod
    def detect_columns(df):
        """Detect string ID and source columns, return both"""
        # String ID column detection
        str_id_names = ['strId', 'ID', 'strID', '字符串', 'id', 'StringID', 'string_id', 'KEY_NAME', "SOURCE"]
        str_id_col = None
        for col in df.columns:
            if col in str_id_names:
                str_id_col = col
                break

        # Source column detection  
        source_names = ['EN', 'English', 'Source', 'en', 'english', 'source']
        source_col = None
        for col in df.columns:
            if col in source_names:
                source_col = col
                break

        return str_id_col, source_col

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
