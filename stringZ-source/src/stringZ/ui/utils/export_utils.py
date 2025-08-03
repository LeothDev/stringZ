import io
import time
import pandas as pd
import streamlit as st

def export_dataframe(df, name):
    """Export dataframe to Excel"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)
    
    timestamp = int(time.time())
    st.download_button(
        label="📥 Download Excel File",
        data=buffer.getvalue(),
        file_name=f"stringz_{name}_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
