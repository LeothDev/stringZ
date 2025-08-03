import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.validation.validators import run_validation

def show_validation_tab():
    """LQA validation tab - SIMPLE AND CLEAN"""
    processed_dataset = st.session_state.processed_dataset
    
    st.title("⚠️ LQA Validation")
    st.markdown("**Automated validation for game translation formatting and consistency**")
    
    # Validation controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **This validation checks for:**
        - 🎯 **Token mismatches** (color tags, variables, brackets)
        - 🏷️ **Malformed game tags** (extra characters, unmatched tags)
        - 📝 **Punctuation inconsistencies** (missing or different endings)
        - 🔢 **Numeric value differences** in color tags
        - 🎮 **Game element consistency** (abilities, skills, colors)
        """)
    
    with col2:
        if st.button("🔍 Run Validation", type="primary", use_container_width=True):
            with st.spinner("🔍 Validating translations..."):
                validation_results = run_validation(processed_dataset)
                st.session_state.validation_results = validation_results
                st.success("✅ Validation completed!")
                st.rerun()
    
    # Show validation results if available
    if st.session_state.validation_results:
        results = st.session_state.validation_results
        
        # Summary metrics
        st.subheader("📊 Validation Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Strings", results['total_strings'])
        
        with col2:
            st.metric("Issues Found", results['issues_found'])
        
        with col3:
            st.metric("Critical Issues", results['critical_issues'], 
                     delta=None if results['critical_issues'] == 0 else f"❌ {results['critical_issues']}")
        
        with col4:
            st.metric("Warnings", results['warnings'],
                     delta=None if results['warnings'] == 0 else f"⚠️ {results['warnings']}")
        
        if results['issues_found'] == 0:
            st.success("🎉 **No validation issues found!** Your translations look great.")
            return
        
        # Filter and display options
        st.subheader("🔍 Issue Details")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            issue_filter = st.selectbox(
                "Filter by Issue Type",
                ["All Issues"] + list(set(issue['type'] for issue in results['detailed_issues']))
            )
        
        with col2:
            severity_filter = st.selectbox(
                "Filter by Severity",
                ["All Severities", "CRITICAL", "WARNING"]
            )
        
        with col3:
            per_page = st.selectbox("Issues per page", [10, 25, 50, "All"], index=1)
        
        # Filter issues
        filtered_issues = results['detailed_issues']
        
        if issue_filter != "All Issues":
            filtered_issues = [issue for issue in filtered_issues if issue['type'] == issue_filter]
        
        if severity_filter != "All Severities":
            filtered_issues = [issue for issue in filtered_issues if issue['severity'] == severity_filter]
        
        st.write(f"Showing {len(filtered_issues)} of {results['issues_found']} issues")
        
        # Pagination for issues
        if per_page != "All" and len(filtered_issues) > per_page:
            total_pages = (len(filtered_issues) + per_page - 1) // per_page
            page = st.selectbox("Page", range(1, total_pages + 1))
            
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, len(filtered_issues))
            page_issues = filtered_issues[start_idx:end_idx]
        else:
            page_issues = filtered_issues
        
        # Display issues - SIMPLE AND CLEAN
        for i, issue in enumerate(page_issues, 1):
            severity_icon = "🚨" if issue['severity'] == 'CRITICAL' else "⚠️"
            
            # Create clean header for easy identification
            issue_header = f"{severity_icon} {issue['str_id']} - {issue['type']}"
            
            with st.expander(issue_header, expanded=i<=3):
                
                # SIMPLE ISSUE SUMMARY
                st.markdown("### 📋 Issue Summary")
                
                # Use columns for clean layout
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.markdown("**String ID:**")
                    st.markdown("**Issue:**")
                    st.markdown("**English:**")
                    st.markdown(f"**{processed_dataset.target_lang}:**")
                
                with col2:
                    st.markdown(f"`{issue['str_id']}`")
                    st.markdown(f"{issue['type']} - {issue['detail']}")
                    st.markdown(f"`{issue['en_text']}`")
                    st.markdown(f"`{issue['target_text']}`")
                

        # Export validation results
        st.subheader("📥 Export Validation Report")
        
        # col1, col2 = st.columns(2)
        
        # with col1:
        #     if st.button("📊 Download Issues Report", use_container_width=True):
        #         # Create issues dataframe
        #         issues_data = []
        #         for issue in results['detailed_issues']:
        #             issues_data.append({
        #                 'strId': issue['str_id'],
        #                 'Issue Type': issue['type'],
        #                 'Severity': issue['severity'],
        #                 'Detail': issue['detail'],
        #                 'English Text': issue['en_text'],
        #                 f'{processed_dataset.target_lang} Text': issue['target_text']
        #             })
                
        #         issues_df = pd.DataFrame(issues_data)
        #         export_dataframe(issues_df, "validation_issues")
        
        # with col2:
        #     if st.button("🚨 Download Critical Issues Only", use_container_width=True):
        #         # Create critical issues dataframe
        #         critical_data = []
        #         for issue in results['detailed_issues']:
        #             if issue['severity'] == 'CRITICAL':
        #                 critical_data.append({
        #                     'strId': issue['str_id'],
        #                     'Issue Type': issue['type'],
        #                     'Detail': issue['detail'],
        #                     'English Text': issue['en_text'],
        #                     f'{processed_dataset.target_lang} Text': issue['target_text']
        #                 })
                
        #         if critical_data:
        #             critical_df = pd.DataFrame(critical_data)
        #             export_dataframe(critical_df, "critical_issues")
        #         else:
        #             st.info("No critical issues to export!")

        st.write("WIP - Stay Tuned!")

