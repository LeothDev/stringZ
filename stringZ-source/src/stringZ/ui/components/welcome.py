import streamlit as st

def show_welcome():
    """Show welcome screen with instructions"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Welcome to StringZ! 🎉
        
        ### What this tool does:
        - **🔄 Removes duplicate translations** automatically
        - **🧠 Groups similar strings together** using AI
        - **⚠️ Validates translations** for formatting errors
        
        ### How to get started:
        1. **Upload your Excel file** using the sidebar
        2. **Choose processing options** (deduplication + correlation)
        3. **Click "Process File"** and get optimized results
        4. **Review translations** and **validate** for errors
        5. **Download the cleaned file** ready for translation work
        
        ### File Requirements:
        - Excel format (.xlsx or .xls)
        - Must contain: `strId`, `EN`, and target language columns
        """)
    
    with col2:
        st.markdown("""
        ### 🎯 Benefits:

        **For LQA Team:**
        - No more duplicate work
        - Similar strings grouped together
        - Automated error detection
        - Faster consistency checking
        - Translation validation
        """)
