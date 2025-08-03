import streamlit as st

def show_preview():
    """Show preview of uploaded file before processing"""
    
    dataset = st.session_state.dataset
    
    st.subheader("📋 File Preview")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", len(dataset))
    
    with col2:
        duplicates = len(dataset.get_duplicates())
        st.metric("Duplicate Groups", duplicates)
    
    with col3:
        completion = dataset.get_completion_rate()
        st.metric("Completion Rate", f"{completion:.1f}%")
    
    with col4:
        # Calculate average string length
        avg_length = sum(len(entry.source_text) for entry in dataset.entries) / len(dataset.entries)
        st.metric("Avg String Length", f"{avg_length:.0f}")
    
    # Data preview
    df = dataset.to_dataframe()
    
    # Search functionality
    search_term = st.text_input("🔍 Search in translations", placeholder="Type to search...")
    if search_term:
        mask = (
            df[dataset.source_lang].str.contains(search_term, case=False, na=False) |
            (df[dataset.target_lang].str.contains(search_term, case=False, na=False) if dataset.target_lang in df.columns else False)
        )
        df_display = df[mask]
        st.write(f"Found {len(df_display)} matches")
    else:
        df_display = df.head(100) 
        if len(df) > 100:
            st.write(f"Showing first 100 of {len(df)} entries")
    
    st.dataframe(df_display, use_container_width=True, height=400)
