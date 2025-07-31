import streamlit as st

def show_review_mode():
    """LQA-focused review interface for consistency checking"""
    processed_dataset = st.session_state.processed_dataset
    
    st.title("🔍 Translation Review")
    st.markdown("**Review similar strings grouped together for consistency checking**")
    
    # Get the dataframe
    df = processed_dataset.to_dataframe()
    
    # Simple controls focused on review workflow
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Find specific strings", 
            placeholder="Search for specific content to review...",
            key="review_search"
        )
    
    with col2:
        # Simple per page options with "All" for consistency checking
        per_page_options = [50, 100, 250, "All"]
        entries_per_page = st.selectbox("📄 Per Page", per_page_options, index=1)
    
    with col3:
        # Focus only on translation-relevant filters
        review_filters = ["All Strings", "Missing Translations", "High Priority (>5 uses)"]
        filter_choice = st.selectbox("📋 Show", review_filters)
    
    # Apply focused filters
    filtered_df = df.copy()
    
    # Search filter
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Review-focused filters
    if filter_choice == "Missing Translations":
        filtered_df = filtered_df[filtered_df[processed_dataset.target_lang].isna()]
    elif filter_choice == "High Priority (>5 uses)" and 'Occurrences' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Occurrences'] > 5]
    
    # Show info about the correlation sorting
    if search_term:
        st.info(f"🔍 Found **{len(filtered_df)}** matches. Strings are sorted by similarity to help spot inconsistencies.")
    else:
        st.info("✨ **Strings are automatically sorted by similarity** - similar strings appear together to make consistency checking easier!")
    
    # Stats focused on review work
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Strings to Review", len(filtered_df))
    with col2:
        if processed_dataset.target_lang in filtered_df.columns and len(filtered_df) > 0:
            missing_count = filtered_df[processed_dataset.target_lang].isna().sum()
            st.metric("❌ Missing Translations", missing_count)
    with col3:
        if 'Occurrences' in filtered_df.columns and len(filtered_df) > 0:
            high_priority = (filtered_df['Occurrences'] > 5).sum()
            st.metric("⭐ High Priority", high_priority)
    
    # Pagination or show all
    total_entries = len(filtered_df)
    
    if entries_per_page == "All":
        # Show all entries - great for consistency checking
        page_df = filtered_df.reset_index(drop=True)
        if total_entries > 500:
            st.warning("⚠️ Showing all entries for consistency review. This might take a moment to load.")
        st.caption(f"Showing all {total_entries} strings (sorted by similarity)")
    else:
        # Paginated view
        total_pages = (total_entries + entries_per_page - 1) // entries_per_page
        
        if total_pages > 1:
            page = st.selectbox(
                "📄 Page", 
                range(1, total_pages + 1), 
                format_func=lambda x: f"Page {x} of {total_pages}"
            )
            
            start_idx = (page - 1) * entries_per_page
            end_idx = min(start_idx + entries_per_page, total_entries)
            page_df = filtered_df.iloc[start_idx:end_idx].reset_index(drop=True)
            
            st.caption(f"Showing strings {start_idx + 1}-{end_idx} of {total_entries} (sorted by similarity)")
        else:
            page_df = filtered_df.reset_index(drop=True)
    
    # Column configuration optimized for translation review
    column_config = {
        "strId": st.column_config.TextColumn(
            "ID", 
            width="small",
            help="String identifier"
        ),
        processed_dataset.source_lang: st.column_config.TextColumn(
            "English", 
            width="large",
            help="Source text to translate"
        ),
    }
    
    if processed_dataset.target_lang in page_df.columns:
        column_config[processed_dataset.target_lang] = st.column_config.TextColumn(
            processed_dataset.target_lang, 
            width="large",
            help=f"Translation in {processed_dataset.target_lang}"
        )
    
    if 'Occurrences' in page_df.columns:
        column_config["Occurrences"] = st.column_config.NumberColumn(
            "Uses", 
            width="small",
            help="How many times this string appears in the game"
        )
    
    # Display the review table
    st.dataframe(
        page_df,
        use_container_width=True,
        height=600 if entries_per_page != "All" else None,
        column_config=column_config,
        hide_index=True
    )
    
    # Simple export for review work
    st.subheader("📥 Export for Translation")
    col1, col2 = st.columns(2)
    st.write("WIP - Stay Tuned!")
    
    # with col1:
    #     if st.button("📊 Export Current View", use_container_width=True):
    #         export_dataframe(page_df, "review_current")
    
    # with col2:
    #     if st.button("📋 Export All Filtered", use_container_width=True):
    #         export_dataframe(filtered_df, "review_filtered")

