import streamlit as st
    
def apply_custom_styles():
    st.markdown("""
        <style>
        .stDataFrame [data-testid="stDataFrameResizable"] div[data-testid="cell"] {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            max-width: 300px !important;
            overflow-wrap: break-word !important;
        }
        .stDataFrame [data-testid="stDataFrameResizable"] {
            font-size: 14px;
        }
        .copy-box {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin: 5px 0;
            font-family: monospace;
            word-break: break-all;
        }
        </style>
        """, unsafe_allow_html=True)
