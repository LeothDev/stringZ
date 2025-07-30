import streamlit as st
import html
import pandas as pd
import io
import time
import sys
import os
import re
from collections import defaultdict

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import our core modules
from stringZ.models.data_models import TranslationDataset
from stringZ.core.processor import TranslationProcessor, ProcessingConfig

# Configure Streamlit
st.set_page_config(
    page_title="StringZ - ZGAME Translation Tool",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'dataset' not in st.session_state:
    st.session_state.dataset = None
if 'processed_dataset' not in st.session_state:
    st.session_state.processed_dataset = None
if 'processing_stats' not in st.session_state:
    st.session_state.processing_stats = None
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None

# Game mechanics keywords and validation functions (from your script)
STRICT_TOKENS = ["\\n", "<", ">", "{", "}", "%", "[", "]"]
# TODO: Use it in the future. But actually implement a way to integrate the Glossary
MECHANICS_KEYWORDS = [
    "damage", "defense", "attack", "health", "mana", "energy", "critical", "crit",
    "buff", "debuff", "skill", "ability", "cooldown", "duration", "level", "tier",
    "upgrade", "enhance", "bonus", "penalty", "effect", "passive", "active",
    "speed", "armor", "resistance", "penetration", "accuracy", "dodge", "block",
    "heal", "shield", "stun", "silence", "freeze", "burn", "poison", "bleed"
]

def extract_game_elements(text):
    """Extract all game-specific elements from text"""
    elements = {
        'color_tags': [],
        'ability_refs': [],
        'skill_vars': [],
        'color_values': [],
        'nested_structures': []
    }
    
    # Extract color tags with their hex values
    color_pattern = r'<color[^>]*>.*?</color>'
    color_matches = re.findall(color_pattern, text)
    elements['color_tags'] = color_matches
    
    # Extract color values from color tags
    color_value_pattern = r'<color[=]([^>]+)>'
    color_values = re.findall(color_value_pattern, text)
    elements['color_values'] = color_values
    
    # Extract ability references [numbers]
    ability_pattern = r'\[(\d+)\]'
    elements['ability_refs'] = re.findall(ability_pattern, text)
    
    # Extract skill variables {skm1}, {skm2}, etc.
    skill_pattern = r'\{(skm\d+)\}'
    elements['skill_vars'] = re.findall(skill_pattern, text)
    
    return elements

def count_enhanced_tokens(text):
    """Enhanced token counting including game elements"""
    counts = defaultdict(int)
    
    # Basic token counting
    for token in STRICT_TOKENS:
        counts[token] = text.count(token)
    
    # Game-specific counting
    game_elements = extract_game_elements(text)
    
    # Count color tags
    counts["<color>"] = len(re.findall(r'<color[^>]*>', text))
    counts["</color>"] = text.count("</color>")
    
    # Count ability references
    counts["ability_refs"] = len(game_elements['ability_refs'])
    
    # Count skill variables
    counts["skill_vars"] = len(game_elements['skill_vars'])
    
    return counts, game_elements

def detect_malformed_tags(text):
    """Detect various types of malformed HTML-like tags"""
    issues = []
    
    # Malformed color tags with extra > characters
    if re.search(r'</color>>+', text):
        issues.append("Extra '>' after closing color tag")
    
    if re.search(r'<color=[^>]*>>[^<]*', text):
        issues.append("Extra '>' after opening color tag")
    
    # Check for unmatched color tag counts
    open_tags = len(re.findall(r'<color[^>]*>', text))
    close_tags = text.count("</color>")
    
    if open_tags != close_tags:
        issues.append(f"Unmatched color tags: {open_tags} open, {close_tags} close")
    
    # Malformed ability references
    if re.search(r'\[+\d+\]+', text):
        malformed_abilities = re.findall(r'\[+\d+\]+', text)
        for match in malformed_abilities:
            if match.count('[') > 1 or match.count(']') > 1:
                issues.append(f"Malformed ability reference: {match}")
    
    # Malformed skill variables
    if re.search(r'\{+skm\d+\}+', text):
        malformed_skills = re.findall(r'\{+skm\d+\}+', text)
        for match in malformed_skills:
            if match.count('{') > 1 or match.count('}') > 1:
                issues.append(f"Malformed skill variable: {match}")
    
    return issues

def detect_punctuation_inconsistencies(en_text, target_text):
    """Detect punctuation inconsistencies between EN and target text"""
    issues = []
    
    en_clean = en_text.strip()
    target_clean = target_text.strip()
    
    if not en_clean or not target_clean:
        return issues
    
    en_last_char = en_clean[-1]
    target_last_char = target_clean[-1]
    
    punctuation_marks = {'.', '!', '?', ':', ';', ','}
    
    # Check ending punctuation consistency
    en_ends_with_punct = en_last_char in punctuation_marks
    target_ends_with_punct = target_last_char in punctuation_marks
    
    # Flag when English HAS punctuation but target is MISSING it
    if en_ends_with_punct and not target_ends_with_punct:
        issues.append(f"Missing ending punctuation: EN ends with '{en_last_char}' but target ends with '{target_last_char}'")
    elif en_ends_with_punct and target_ends_with_punct and en_last_char != target_last_char:
        issues.append(f"Different ending punctuation: EN '{en_last_char}' vs target '{target_last_char}'")
    
    return issues

def detect_content_inconsistencies(en_text, target_text):
    """Detect content inconsistencies within color tags and skill variables"""
    issues = []
    
    # Extract numeric values from color tags
    en_color_contents = re.findall(r'<color[^>]*>([^<]+)</color>', en_text)
    target_color_contents = re.findall(r'<color[^>]*>([^<]+)</color>', target_text)
    
    en_numbers = []
    target_numbers = []
    
    for content in en_color_contents:
        numbers = re.findall(r'\d+(?:\.\d+)?%?', content)
        en_numbers.extend(numbers)
    
    for content in target_color_contents:
        numbers = re.findall(r'\d+(?:\.\d+)?%?', content)
        target_numbers.extend(numbers)
    
    # Compare numeric values (using sets to ignore order)
    en_numbers_set = set(en_numbers)
    target_numbers_set = set(target_numbers)
    
    if en_numbers_set != target_numbers_set:
        missing_numbers = list(en_numbers_set - target_numbers_set)
        extra_numbers = list(target_numbers_set - en_numbers_set)
        
        if missing_numbers:
            issues.append(f"Missing numbers: {missing_numbers}")
        if extra_numbers:
            issues.append(f"Extra numbers: {extra_numbers}")
    
    return issues

def validate_translation_pair(str_id, en_text, target_text, target_lang):
    """Validate a single translation pair - returns list of issues"""
    issues = []
    
    if not en_text or not target_text:
        return issues
    
    # Enhanced token counting
    en_counts, en_elements = count_enhanced_tokens(en_text)
    target_counts, target_elements = count_enhanced_tokens(target_text)
    
    # Check basic token mismatches
    for token in en_counts:
        if en_counts[token] != target_counts[token]:
            issues.append({
                'type': 'Token Mismatch',
                'severity': 'CRITICAL',
                'detail': f"{token}: EN={en_counts[token]} vs {target_lang}={target_counts[token]}"
            })
    
    # Check game element consistency (fix color values comparison using sets)
    if set(en_elements['color_values']) != set(target_elements['color_values']):
        missing_colors = list(set(en_elements['color_values']) - set(target_elements['color_values']))
        extra_colors = list(set(target_elements['color_values']) - set(en_elements['color_values']))
        
        color_details = []
        if missing_colors:
            color_details.append(f"Missing colors: {missing_colors}")
        if extra_colors:
            color_details.append(f"Extra colors: {extra_colors}")
        
        if color_details:
            issues.append({
                'type': 'Color Values Mismatch',
                'severity': 'CRITICAL',
                'detail': "; ".join(color_details)
            })
    
    if set(en_elements['ability_refs']) != set(target_elements['ability_refs']):
        missing_abilities = list(set(en_elements['ability_refs']) - set(target_elements['ability_refs']))
        extra_abilities = list(set(target_elements['ability_refs']) - set(en_elements['ability_refs']))
        
        ability_details = []
        if missing_abilities:
            ability_details.append(f"Missing abilities: {missing_abilities}")
        if extra_abilities:
            ability_details.append(f"Extra abilities: {extra_abilities}")
        
        if ability_details:
            issues.append({
                'type': 'Ability References Mismatch',
                'severity': 'CRITICAL',
                'detail': "; ".join(ability_details)
            })
    
    if set(en_elements['skill_vars']) != set(target_elements['skill_vars']):
        missing_skills = list(set(en_elements['skill_vars']) - set(target_elements['skill_vars']))
        extra_skills = list(set(target_elements['skill_vars']) - set(en_elements['skill_vars']))
        
        skill_details = []
        if missing_skills:
            skill_details.append(f"Missing skills: {missing_skills}")
        if extra_skills:
            skill_details.append(f"Extra skills: {extra_skills}")
        
        if skill_details:
            issues.append({
                'type': 'Skill Variables Mismatch',
                'severity': 'CRITICAL',
                'detail': "; ".join(skill_details)
            })
    
    # Check for malformed tags
    en_malformed = detect_malformed_tags(en_text)
    target_malformed = detect_malformed_tags(target_text)
    
    for malformed in en_malformed:
        issues.append({
            'type': 'EN Malformed Tag',
            'severity': 'CRITICAL',
            'detail': malformed
        })
    
    for malformed in target_malformed:
        issues.append({
            'type': f'{target_lang} Malformed Tag',
            'severity': 'CRITICAL',
            'detail': malformed
        })
    
    # Check punctuation inconsistencies
    punct_issues = detect_punctuation_inconsistencies(en_text, target_text)
    for punct_issue in punct_issues:
        issues.append({
            'type': 'Punctuation Mismatch',
            'severity': 'WARNING',
            'detail': punct_issue
        })
    
    # Check content inconsistencies
    content_issues = detect_content_inconsistencies(en_text, target_text)
    for content_issue in content_issues:
        issues.append({
            'type': 'Content Mismatch',
            'severity': 'CRITICAL',
            'detail': content_issue
        })
    
    return issues

def run_validation(dataset):
    """Run validation on the entire dataset"""
    validation_results = {
        'total_strings': len(dataset.entries),
        'issues_found': 0,
        'critical_issues': 0,
        'warnings': 0,
        'detailed_issues': []
    }
    
    for entry in dataset.entries:
        if entry.target_text:  # Only validate if translation exists
            issues = validate_translation_pair(
                entry.str_id, 
                entry.source_text, 
                entry.target_text, 
                dataset.target_lang
            )
            
            for issue in issues:
                validation_results['issues_found'] += 1
                if issue['severity'] == 'CRITICAL':
                    validation_results['critical_issues'] += 1
                else:
                    validation_results['warnings'] += 1
                
                validation_results['detailed_issues'].append({
                    'str_id': entry.str_id,
                    'en_text': entry.source_text,
                    'target_text': entry.target_text,
                    **issue
                })
    
    return validation_results

def main():
    # Header
    st.image(image="https://cdn.moogold.com/2024/10/watcher-of-realms.jpg", width=100)
    st.title("StringZ")
    st.markdown("**Translation QA Tool for ZGAME**")
    st.markdown("*Deduplicate, sort by similarity, and validate translations*")
    
    # Custom CSS for better text wrapping
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
    
    # Check if we have processed data to show tabs
    if st.session_state.processed_dataset is not None:
        # Show tabs when data is processed
        tab1, tab2, tab3 = st.tabs(["📊 Results", "🔍 Review Translations", "⚠️ LQA Validation"])
        
        with tab1:
            show_results()
        
        with tab2:
            show_review_mode()
            
        with tab3:
            show_validation_tab()
            
        # Sidebar with reset option
        with st.sidebar:
            st.header("🔄 Process New File")
            
            if st.button("🆕 Start Over", type="secondary", use_container_width=True):
                st.session_state.dataset = None
                st.session_state.processed_dataset = None
                st.session_state.processing_stats = None
                st.session_state.validation_results = None
                st.rerun()
            
            st.markdown("---")
            dataset = st.session_state.processed_dataset
            st.write(f"📝 **{len(dataset)}** entries")
            st.write(f"🌍 **{dataset.source_lang}** → **{dataset.target_lang}**")
            
            # Quick stats in sidebar
            df = dataset.to_dataframe()
            if 'Occurrences' in df.columns:
                avg_occ = df['Occurrences'].mean()
                max_occ = df['Occurrences'].max()
                st.write(f"📊 Avg occurrences: **{avg_occ:.1f}**")
                st.write(f"🔥 Max occurrences: **{max_occ}**")
            
            if dataset.target_lang in df.columns:
                completion_rate = (df[dataset.target_lang].notna().sum() / len(df) * 100)
                st.write(f"✅ Completion: **{completion_rate:.1f}%**")
    
    else:
        # Original workflow - sidebar controls + main content
        with st.sidebar:
            st.header("⚙️ Processing Controls")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Upload Translation File",
                type=['xlsx', 'xls'],
                help="Upload Excel file with strId, EN, and target language columns"
            )
            
            if uploaded_file:
                # Load and analyze file
                if st.session_state.dataset is None:
                    with st.spinner("Loading file..."):
                        try:
                            df = pd.read_excel(uploaded_file)
                            
                            # Language selection
                            st.subheader("🌍 Select Target Language")
                            
                            # Find potential language columns (exclude strId and EN)
                            lang_columns = [col for col in df.columns if col not in ["strId", "EN"]]
                            
                            if not lang_columns:
                                st.error("No target language columns found! Make sure your file has columns other than 'strId' and 'EN'.")
                                return
                            
                            # Let user select target language
                            selected_language = st.selectbox(
                                "Choose target language:",
                                options=lang_columns,
                                help="All other language columns will be removed"
                            )
                            
                            # Button to confirm language selection and load data
                            if st.button("✅ Load Data", type="primary"):
                                with st.spinner(f"Loading data with {selected_language}..."):
                                    # Filter dataframe to keep only selected columns
                                    columns_to_keep = ["strId", "EN", selected_language]
                                    df_filtered = df[columns_to_keep].copy()
                                    
                                    # Create dataset from filtered dataframe
                                    st.session_state.dataset = TranslationDataset.from_dataframe(
                                        df_filtered, 
                                        source_col="EN",
                                        target_col=selected_language,
                                        str_id_col="strId"
                                    )
                                    
                                    st.success(f"✅ Loaded {len(st.session_state.dataset)} entries")
                                    st.rerun()
                            
                            return  # Don't continue until language is selected
                            
                        except Exception as e:
                            st.error(f"Error loading file: {str(e)}")
                            return
                
                # Show processing options
                dataset = st.session_state.dataset
                st.subheader("📊 File Information")
                st.write(f"**{len(dataset)}** entries loaded")
                
                st.subheader("🔧 Processing Options")
                
                # Main settings
                remove_duplicates = st.checkbox("Remove Duplicates", value=True)
                sort_by_correlation = st.checkbox("Sort by Similarity", value=True)
                
                correlation_strategy = st.selectbox(
                    "Sorting Method",
                    ["hybrid", "substring", "semantic"],
                    help="hybrid: Best of substring + semantic"
                ) if sort_by_correlation else "hybrid"
                
                # Advanced settings in expander
                with st.expander("⚙️ Advanced Settings"):
                    if sort_by_correlation and correlation_strategy in ["semantic", "hybrid"]:
                        similarity_threshold = st.slider(
                            "Similarity Threshold",
                            min_value=0.5,
                            max_value=0.9,
                            value=0.7,
                            step=0.1
                        )
                        max_cluster_size = st.slider(
                            "Max Cluster Size",
                            min_value=5,
                            max_value=30,
                            value=15,
                            step=5
                        )
                    else:
                        similarity_threshold = 0.7
                        max_cluster_size = 15
                    
                    if sort_by_correlation and correlation_strategy in ["substring", "hybrid"]:
                        min_substring_length = st.slider(
                            "Min Substring Length",
                            min_value=3,
                            max_value=15,
                            value=5,
                            step=1
                        )
                    else:
                        min_substring_length = 5
                
                # Process button
                if st.button("🚀 Process File", type="primary", use_container_width=True):
                    process_file(
                        dataset,
                        remove_duplicates,
                        "keep_first_with_occurrences",
                        sort_by_correlation,
                        correlation_strategy,
                        similarity_threshold,
                        max_cluster_size,
                        min_substring_length 
                    )
        
        # Main content area
        if st.session_state.dataset is not None:
            show_preview()
        else:
            show_welcome()


def process_file(dataset, remove_duplicates, dedup_strategy, sort_by_correlation, 
                correlation_strategy, similarity_threshold, max_cluster_size, min_substring_length):
    """Process the uploaded file with given settings"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("⚙️ Initializing processing...")
        progress_bar.progress(20)
        
        # Create processing configuration
        config = ProcessingConfig(
            remove_duplicates=remove_duplicates,
            deduplication_strategy=dedup_strategy,
            sort_by_correlation=sort_by_correlation,
            correlation_strategy=correlation_strategy,
            similarity_threshold=similarity_threshold,
            max_cluster_size=max_cluster_size,
            min_substring_length=min_substring_length
        )
        
        processor = TranslationProcessor(config)
        
        status_text.text("🔄 Processing dataset...")
        progress_bar.progress(60)
        
        processed_dataset = processor.process(dataset)
        
        progress_bar.progress(90)
        status_text.text("📊 Generating statistics...")
        
        # Store results
        st.session_state.processed_dataset = processed_dataset
        st.session_state.processing_stats = processor.get_processing_stats(processed_dataset)
        
        progress_bar.progress(100)
        status_text.text("✅ Processing completed!")
        
        # Clear progress after a moment
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        st.success("✅ Processing completed!")
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Processing failed: {str(e)}")
        st.exception(e)


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

def format_text_for_visualizer(text):
    """
    Format text for visualizer display - converts game markup to HTML
    
    Args:
        text: str - original text with game markup
    
    Returns:
        tuple: (raw_text, formatted_text)
    """
    if not text or pd.isna(text) or text == 'nan':
        return '', ''
    
    text = str(text)
    
    # RAW DATA: HTML encode everything for debugging view
    raw_text = html.escape(text)
    
    # FORMATTED DATA: Convert game markup to proper HTML
    formatted_text = text
    
    # Convert color tags: <color="#eadca2">text</color> -> <span style="color: #eadca2;">text</span>
    color_pattern = r'<color[=]?"([^">]+)"?>([^<]*)</color>'
    formatted_text = re.sub(color_pattern, r'<span style="color: \1;">\2</span>', formatted_text)
    
    # Convert line breaks: \\n -> <br>
    formatted_text = formatted_text.replace('\\n', '<br>')
    
    # Convert other common patterns
    formatted_text = formatted_text.replace('\\t', '&nbsp;&nbsp;&nbsp;&nbsp;')  # tabs to spaces
    
    return raw_text, formatted_text

def generate_visualizer_html(dataset, original_filename=None):
    """
    Generate interactive HTML visualizer file from processed dataset
    
    Args:
        dataset: TranslationDataset - the processed dataset
        original_filename: str - original filename for naming
    
    Returns:
        str: Complete HTML content ready for download
    """
    
    # Extract data from dataset
    df = dataset.to_dataframe()
    
    # Determine target language column name
    target_lang = dataset.target_lang or "Target"
    
    # Create headers array - cleaner layout focused on LQA needs
    headers = ["strId", dataset.source_lang, target_lang, "Occurrences", "State", "Notes"]
    
    # Generate raw data array (JavaScript format)
    raw_data_rows = []
    formatted_data_rows = []
    
    for _, row in df.iterrows():
        # Extract values
        str_id = str(row.get('strId', ''))
        en_text = str(row.get(dataset.source_lang, ''))
        target_text = str(row.get(target_lang, '')) if target_lang in df.columns else ''
        occurrences = int(row.get('Occurrences', 1))  # Default to 1 if missing
        
        # Format text properly for both raw and formatted views
        raw_en, formatted_en = format_text_for_visualizer(en_text)
        raw_target, formatted_target = format_text_for_visualizer(target_text)
        
        # Create raw data row (HTML encoded for debugging)
        raw_row = [str_id, raw_en, raw_target, str(occurrences), "", ""]
        
        # Create formatted data row (proper HTML for display)
        formatted_row = [
            html.escape(str_id),  # ID is always escaped
            formatted_en,         # EN text with HTML formatting
            formatted_target,     # Target text with HTML formatting
            str(occurrences),     # Occurrences count - useful for prioritization
            "",                   # State column - empty for user input
            ""                    # Notes column - empty for user input
        ]
        
        raw_data_rows.append(raw_row)
        formatted_data_rows.append(formatted_row)
    
    # Convert to JavaScript array format
    def python_list_to_js_array(data_rows):
        js_rows = []
        for row in data_rows:
            # Properly escape each string for JavaScript
            escaped_row = []
            for item in row:
                if isinstance(item, str):
                    # Escape quotes and special characters for JavaScript
                    escaped = item.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                    escaped_row.append(f'"{escaped}"')
                else:
                    escaped_row.append(f'"{str(item)}"')
            js_rows.append('[' + ', '.join(escaped_row) + ']')
        return '[' + ', '.join(js_rows) + ']'
    
    raw_data_js = python_list_to_js_array(raw_data_rows)
    formatted_data_js = python_list_to_js_array(formatted_data_rows)
    headers_js = '[' + ', '.join(f'"{h}"' for h in headers) + ']'
    
    # Calculate word count for visualizer header
    target_word_count = 0
    if target_lang in df.columns:
        target_word_count = df[target_lang].dropna().astype(str).apply(lambda x: len(x.split())).sum()
    
    # Generate title
    if original_filename:
        clean_filename = re.sub(r'\.[^.]+$', '', original_filename)  # Remove extension
        title = f"StringZ Visualizer - {clean_filename}"
    else:
        title = f"StringZ Visualizer - {target_lang} Translation Review"
   
    # HTML template with data injection
    html_content = f'''<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <style>
      :root {{
        /* Light mode colors */
        --bg-primary: #f8f9fa;
        --bg-secondary: white;
        --bg-banner: #f8f9fa;
        --text-primary: #333;
        --text-secondary: #6c757d;
        --text-muted: #495057;
        --border-color: #dee2e6;
        --table-header-bg: #f8f9fa;
        --table-border: #dee2e6;
        --button-bg: #6c757d;
        --button-hover: #5a6268;
        --input-bg: white;
      }}
      
      [data-theme="dark"] {{
        /* Dark mode colors */
        --bg-primary: #1a1a1a;
        --bg-secondary: #2d2d2d;
        --bg-banner: #343a40;
        --text-primary: #f8f9fa;
        --text-secondary: #adb5bd;
        --text-muted: #ced4da;
        --border-color: #495057;
        --table-header-bg: #343a40;
        --table-border: #495057;
        --button-bg: #495057;
        --button-hover: #5a6268;
        --input-bg: #343a40;
      }}
      
      body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: var(--bg-primary);
        margin: 0;
        padding: 0;
        color: var(--text-primary);
        transition: background-color 0.3s ease, color 0.3s ease;
      }}
      
      .toggle-btn {{
        position: fixed;
        top: 15px;
        left: 15px;
        z-index: 9999;
        padding: 8px 16px;
        background-color: var(--button-bg);
        color: white;
        border: 1px solid var(--button-bg);
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
        font-size: 14px;
        transition: background-color 0.2s ease;
      }}
      
      .toggle-btn:hover {{
        background-color: var(--button-hover);
        border-color: var(--button-hover);
      }}
      
      .dark-mode-btn {{
        position: fixed;
        top: 15px;
        left: 120px;
        z-index: 9999;
        padding: 8px 16px;
        background-color: var(--button-bg);
        color: white;
        border: 1px solid var(--button-bg);
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
        font-size: 14px;
        transition: background-color 0.2s ease;
      }}
      
      .dark-mode-btn:hover {{
        background-color: var(--button-hover);
        border-color: var(--button-hover);
      }}
      
      #clearState {{
        float: left;
        margin-right: 15px;
        margin-bottom: 15px;
        padding: 8px 16px;
        background-color: #dc3545;
        color: white;
        border: 1px solid #dc3545;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
        font-size: 14px;
        transition: background-color 0.2s ease;
      }}
      
      #clearState:hover {{
        background-color: #c82333;
        border-color: #bd2130;
      }}
      
      .container {{
        padding: 70px 30px 30px 30px;
        background: var(--bg-secondary);
        margin: 0;
        min-height: 100vh;
        transition: background-color 0.3s ease;
      }}
      
      .info-banner {{
        background-color: var(--bg-banner);
        border: 1px solid var(--border-color);
        color: var(--text-muted);
        padding: 20px;
        margin-bottom: 25px;
        border-radius: 4px;
        text-align: center;
        transition: background-color 0.3s ease, border-color 0.3s ease;
      }}
      
      .info-banner h2 {{
        margin: 0 0 10px 0;
        font-size: 24px;
        font-weight: 600;
        color: var(--text-primary);
      }}
      
      .info-banner p {{
        margin: 0;
        font-size: 14px;
        color: var(--text-secondary);
      }}
      
      #myTable {{
        border: 1px solid var(--border-color);
        border-radius: 4px;
        overflow: hidden;
        transition: border-color 0.3s ease;
      }}
      
      #myTable td {{
        user-select: text !important;
        padding: 12px 8px;
        vertical-align: top;
        border-bottom: 1px solid var(--table-border);
        background-color: var(--bg-secondary);
        color: var(--text-primary);
        transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
      }}
      
      #myTable th {{
        background-color: var(--table-header-bg);
        border-bottom: 2px solid var(--border-color);
        color: var(--text-muted);
        font-weight: 600;
        padding: 15px 8px;
        text-align: center;
        transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
      }}
      
      /* Enhanced styling for different columns */
      #myTable td:first-child {{
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: var(--text-secondary);
        max-width: 120px;
      }}
      
      #myTable td:nth-child(2), #myTable td:nth-child(3) {{
        line-height: 1.4;
        max-width: 300px;
        word-wrap: break-word;
      }}
      
      #myTable td:nth-child(4) {{
        text-align: center;
        font-weight: 600;
        color: var(--text-muted);
        font-size: 14px;
      }}
      
      #myTable td:nth-child(6) {{
        min-width: 150px;
        max-width: 200px;
      }}
      
      select.state-select {{
        width: 100%;
        font-weight: 500;
        padding: 6px 8px;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        font-size: 14px;
        background-color: var(--input-bg);
        color: var(--text-primary);
        transition: all 0.3s ease;
      }}
      
      input.notes-input {{
        width: 100%;
        padding: 6px 8px;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        font-size: 12px;
        background-color: var(--input-bg);
        color: var(--text-primary);
        transition: all 0.3s ease;
      }}
      
      input.notes-input:focus {{
        outline: none;
        border-color: #80bdff;
        box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
      }}
      
      input.notes-input::placeholder {{
        color: var(--text-secondary);
        font-style: italic;
      }}
      
      select.state-select:focus {{
        outline: none;
        border-color: #80bdff;
        box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
      }}
      
      select.state-select.pass {{
        color: #28a745;
        border-color: #28a745;
      }}
      
      select.state-select.fail {{
        color: #dc3545;
        border-color: #dc3545;
      }}
      
      /* DataTables styling */
      .dataTables_wrapper {{
        color: var(--text-primary);
      }}
      
      .dataTables_wrapper .dataTables_length,
      .dataTables_wrapper .dataTables_filter,
      .dataTables_wrapper .dataTables_info,
      .dataTables_wrapper .dataTables_paginate {{
        margin: 15px 0;
      }}
      
      .dataTables_wrapper .dataTables_filter input {{
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 6px 12px;
        margin-left: 8px;
        background-color: var(--input-bg);
        color: var(--text-primary);
        transition: all 0.3s ease;
      }}
      
      .dataTables_wrapper .dataTables_length select {{
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 4px 8px;
        margin: 0 8px;
        background-color: var(--input-bg);
        color: var(--text-primary);
        transition: all 0.3s ease;
      }}
      
      .dataTables_wrapper .dataTables_paginate .paginate_button {{
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 6px 12px;
        margin: 0 2px;
        background-color: var(--input-bg);
        color: var(--text-primary) !important;
        transition: all 0.3s ease;
      }}
      
      .dataTables_wrapper .dataTables_paginate .paginate_button:hover {{
        background-color: var(--bg-banner);
        border-color: var(--text-secondary);
      }}
      
      .dataTables_wrapper .dataTables_paginate .paginate_button.current {{
        background-color: #007bff;
        border-color: #007bff;
        color: white !important;
      }}
    </style>
  </head>
  <body>
    <button class="toggle-btn" onclick="toggleData()">Show Raw</button>
    <button class="dark-mode-btn" onclick="toggleDarkMode()">🌙 Dark</button>
    <div class="container">
      <div class="info-banner">
        <h2>{html.escape(title)}</h2>
        <p>📊 <strong>{len(df)}</strong> strings • 🌍 <strong>{dataset.source_lang}</strong> → <strong>{target_lang}</strong> • 📝 <strong>{target_word_count:,}</strong> words • 🛠️ Generated by StringZ</p>
      </div>
      <button id="clearState">Clear All States</button>
      <table id="myTable" class="display" style="width:100%"></table>
    </div>
    <script>
      const headers = {headers_js};
            const rawData = {raw_data_js};
            const formattedData = {formatted_data_js};
            let showingRaw = false;
            let tableData = formattedData;
            let dataTable;
        
            function getStateKey(index) {{
                return "state_{html.escape(title.replace(' ', '_'))}_row_" + index;
            }}
            
            function getNotesKey(index) {{
                return "notes_{html.escape(title.replace(' ', '_'))}_row_" + index;
            }}
        
            function generateRowWithState(row, idx) {{
                const savedState = localStorage.getItem(getStateKey(idx)) || "";
                const savedNotes = localStorage.getItem(getNotesKey(idx)) || "";
                
                const selectHTML = '<select class="state-select ' + savedState.toLowerCase() + '">' +
                    '<option value="" ' + (savedState === "" ? "selected" : "") + '></option>' +
                    '<option value="Pass" ' + (savedState === "Pass" ? "selected" : "") + '>Pass</option>' +
                    '<option value="Fail" ' + (savedState === "Fail" ? "selected" : "") + '>Fail</option>' +
                    '</select>';
                
                const notesHTML = '<input type="text" class="notes-input" value="' + 
                    savedNotes.replace(/"/g, '&quot;') + 
                    '" placeholder="Personal notes..." maxlength="200">';
                
                const newRow = row.slice();
                const stateIndex = headers.indexOf("State");
                const notesIndex = headers.indexOf("Notes");
                newRow[stateIndex] = selectHTML;
                newRow[notesIndex] = notesHTML;
                return newRow;
            }}
        
            function renderData(data) {{
                tableData = data;
                const transformed = data.map((row, idx) => generateRowWithState(row, idx));
        
                if (!dataTable) {{
                    dataTable = $('#myTable').DataTable({{
                        data: transformed,
                        columns: headers.map(h => ({{ title: h }})),
                        scrollX: true,
                        paging: true,
                        searching: true,
                        ordering: true,
                        deferRender: true,
                        lengthMenu: [[-1, 10, 25, 50], ["All", 10, 25, 50]],
                        order: [],
                        columnDefs: [
                            {{
                                targets: headers.indexOf("State"),
                                orderable: true
                            }}
                        ]
                    }});
        
                    $('#myTable tbody').on('change', 'select.state-select', function () {{
                        const rowIdx = dataTable.row($(this).closest('tr')).index();
                        const value = $(this).val();
                        localStorage.setItem(getStateKey(rowIdx), value);
                        this.className = "state-select " + value.toLowerCase();
                    }});
                    
                    $('#myTable tbody').on('input', 'input.notes-input', function () {{
                        const rowIdx = dataTable.row($(this).closest('tr')).index();
                        const value = $(this).val();
                        localStorage.setItem(getNotesKey(rowIdx), value);
                    }});
                }} else {{
                    const currentPage = dataTable.page();
                    const currentLength = dataTable.page.len();
                    dataTable.clear().rows.add(transformed).draw(false);
                    dataTable.page.len(currentLength).draw();
                    dataTable.page(currentPage).draw(false);
                }}
            }}
        
            function toggleData() {{
                showingRaw = !showingRaw;
                renderData(showingRaw ? rawData : formattedData);
                
                // Update button text
                const btn = document.querySelector('.toggle-btn');
                btn.textContent = showingRaw ? 'Show Formatted' : 'Show Raw';
            }}
        
            function clearAllStates() {{
                const total = tableData.length;
                let clearedCount = 0;
                
                for (let i = 0; i < total; i++) {{
                    const stateKey = getStateKey(i);
                    const notesKey = getNotesKey(i);
                    
                    if (localStorage.getItem(stateKey)) {{
                        localStorage.removeItem(stateKey);
                        clearedCount++;
                    }}
                    if (localStorage.getItem(notesKey)) {{
                        localStorage.removeItem(notesKey);
                    }}
                }}
                
                renderData(tableData);
                
                // Better user feedback
                if (clearedCount > 0) {{
                    alert(`✅ Cleared ${{clearedCount}} review states and all notes!`);
                }} else {{
                    alert('ℹ️ No review states to clear.');
                }}
            }}
        
            function getProgress() {{
                const total = tableData.length;
                let reviewed = 0;
                let passed = 0;
                let failed = 0;
                
                for (let i = 0; i < total; i++) {{
                    const state = localStorage.getItem(getStateKey(i));
                    if (state) {{
                        reviewed++;
                        if (state === 'Pass') passed++;
                        if (state === 'Fail') failed++;
                    }}
                }}
                
                return {{ total, reviewed, passed, failed }};
            }}
            
            function updateProgressDisplay() {{
                const progress = getProgress();
                const percentage = Math.round((progress.reviewed / progress.total) * 100);
                
                // Update the info banner with progress
                const banner = document.querySelector('.info-banner p');
                if (banner) {{
                    const originalText = banner.textContent.split('•')[0] + '•';
                    banner.innerHTML = `${{originalText}} 📊 <strong>${{progress.reviewed}}/${{progress.total}}</strong> reviewed (<strong>${{percentage}}%</strong>) • ✅ <strong>${{progress.passed}}</strong> passed • ❌ <strong>${{progress.failed}}</strong> failed`;
                }}
            }}
        
            function toggleDarkMode() {{
                const body = document.body;
                const btn = document.querySelector('.dark-mode-btn');
                const isDark = body.getAttribute('data-theme') === 'dark';
                
                if (isDark) {{
                    body.removeAttribute('data-theme');
                    btn.textContent = '🌙 Dark';
                    localStorage.setItem('visualizer-theme', 'light');
                }} else {{
                    body.setAttribute('data-theme', 'dark');
                    btn.textContent = '☀️ Light'; 
                    localStorage.setItem('visualizer-theme', 'dark');
                }}
            }}
            
            function initializeTheme() {{
                const savedTheme = localStorage.getItem('visualizer-theme');
                const btn = document.querySelector('.dark-mode-btn');
                
                if (savedTheme === 'dark') {{
                    document.body.setAttribute('data-theme', 'dark');
                    btn.textContent = '☀️ Light';
                }} else {{
                    btn.textContent = '🌙 Dark';
                }}
            }}
        
            $(document).ready(function () {{
                initializeTheme();
                renderData(formattedData);
                $('#clearState').click(clearAllStates);
                
                // Update progress on page load
                updateProgressDisplay();
                
                // Update progress when states change
                $('#myTable tbody').on('change', 'select.state-select', function () {{
                    setTimeout(updateProgressDisplay, 100);
                }});
            }});
    </script>
  </body>
</html>'''
    
    return html_content

def enhanced_file_upload():
    """Enhanced file upload that remembers original filename"""
    uploaded_file = st.file_uploader(
        "Upload Translation File",
        type=['xlsx', 'xls'],
        help="Upload Excel file with strId, EN, and target language columns"
    )
    
    if uploaded_file:
        # Store original filename in session state
        st.session_state.original_filename = uploaded_file.name
    
    return uploaded_file

def show_results():
    """Modified show_results function with visualizer export"""
    
    processed_dataset = st.session_state.processed_dataset
    stats = st.session_state.processing_stats
    summary = stats['processing_summary']
    
    st.subheader("📊 Processing Results")

    # Compute word count
    df = processed_dataset.to_dataframe()
    target_lang = processed_dataset.target_lang
    word_count = 0
    if target_lang in df.columns:
        word_count = df[target_lang].dropna().astype(str).apply(lambda x: len(x.split())).sum()
    
    # Main metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Original Entries", summary['original_count'])
    
    with col2:
        st.metric(
            "Final Entries",
            summary['final_count'],
            delta=-summary['duplicates_removed'] if summary['duplicates_removed'] > 0 else None
        )
    
    with col3:
        st.metric("Duplicates Removed", summary['duplicates_removed'])
    
    with col4:
        st.metric("Groups Created", summary['clusters_created'])

    with col5:
        st.metric(f"{target_lang} Words", f"{word_count:,}")
    
    # MAIN DOWNLOAD SECTION - NEW LAYOUT
    st.subheader("📥 Export Processed Results")
    
    # Two-column layout for main downloads
    col1, col2 = st.columns(2)
    
    with col1:       
        # Generate filename for visualizer
        current_time = int(time.time())
        original_filename = getattr(st.session_state, 'original_filename', None)
        
        if original_filename:
            clean_name = re.sub(r'\.[^.]+$', '', original_filename)
            visualizer_filename = f"Visualizer-{clean_name}.html"
        else:
            visualizer_filename = f"StringZ-Visualizer-{processed_dataset.target_lang}-{current_time}.html"
        
        # Generate visualizer HTML
        try:
            visualizer_html = generate_visualizer_html(processed_dataset, original_filename)
            
            st.download_button(
                label="Download Visualizer",
                data=visualizer_html.encode('utf-8'),
                file_name=visualizer_filename,
                mime="text/html",
                type="primary",
                use_container_width=True,
                help="Interactive HTML file for LQA Raw/Formatted Data"
            )
            
        except Exception as e:
            st.error(f"Error generating visualizer: {str(e)}")
            st.exception(e)
    
    with col2:
        df_processed = processed_dataset.to_dataframe()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_processed.to_excel(writer, sheet_name='Processed_Translations', index=False)
        
        st.download_button(
            label="📊 Download Processed Spreadsheet",
            data=buffer.getvalue(),
            file_name=f"StringZ-Processed-{current_time}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True,
            help="Excel file with processed translations, duplicates removed, and strings organized"
        )       
    
    # Additional download options (smaller)
    st.markdown("---")
    st.markdown("**Additional Export Options:**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Missing translations only
        if processed_dataset.target_lang in df_processed.columns:
            missing_df = df_processed[df_processed[processed_dataset.target_lang].isna()]
            if len(missing_df) > 0:
                missing_buffer = io.BytesIO()
                with pd.ExcelWriter(missing_buffer, engine='openpyxl') as writer:
                    missing_df.to_excel(writer, sheet_name='Missing_Translations', index=False)
                
                st.download_button(
                    label=f"❌ Missing Only ({len(missing_df)} strings)",
                    data=missing_buffer.getvalue(),
                    file_name=f"StringZ-Missing-{current_time}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    with col2:
        # High priority strings (high occurrences)
        if 'Occurrences' in df_processed.columns:
            priority_df = df_processed[df_processed['Occurrences'] > 5]
            if len(priority_df) > 0:
                priority_buffer = io.BytesIO()
                with pd.ExcelWriter(priority_buffer, engine='openpyxl') as writer:
                    priority_df.to_excel(writer, sheet_name='Priority_Strings', index=False)
                
                st.download_button(
                    label=f"⭐ High Priority ({len(priority_df)} strings)",
                    data=priority_buffer.getvalue(),
                    file_name=f"StringZ-Priority-{current_time}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

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


if __name__ == "__main__":
    main()
