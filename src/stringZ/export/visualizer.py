import html
import re
from pathlib import Path
import pandas as pd

def load_template():
    template_path = Path(__file__).parent / "templates" / "visualizer_template.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

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
    template = load_template()

    # Extract data from the dataset
    df = dataset.to_dataframe()
    target_lang = dataset.target_lang or "Target"

    # Words count
    target_word_count = 0
    if target_lang in df.columns:
        target_word_count = df[target_lang].dropna().astype(str).apply(lambda x: len(x.split())).sum()

    # Generate title for the Visualizer
    if original_filename:
        clean_filename = re.sub(r'\.[^.]+$', '', original_filename)
        title = f"StringZ Visualizer - {clean_filename}"
        # title = "StringZ Visualizer"
    else:
        title = f"StringZ Visualizer - {target_lang}"

    is_chinese_mode = (
        target_lang in ['CNTraditional', 'CNSimplified'] and
        'EN' in df.columns and
        (dataset.source_lang in ['CN', 'base'] or 'CN' in df.columns)
    )

    # Headers and Data from the Spreadsheet
    if is_chinese_mode:
        print("DEBUG: - CHINESE DETECTED")
        headers = ["strId", "CN", "EN", target_lang, "Occurrences", "State", "Notes"]
        raw_data_rows, formatted_data_rows = _prepare_chinese_data_rows(df, dataset, target_lang)
    else:
        headers = ["strId", dataset.source_lang, target_lang, "Occurrences", "State", "Notes"]
        raw_data_rows, formatted_data_rows = _prepare_data_rows(df, dataset, target_lang)

    # Convert to JS arrays to be properly injected in the HTML template
    headers_js = '[' + ', '.join(f'"{h}"' for h in headers) + ']'
    raw_data_js = _python_list_to_js_array(raw_data_rows)
    formatted_data_js = _python_list_to_js_array(formatted_data_rows)

    # Replace all placeholders in the Visualizer template
    replacements = {
        '{{TITLE}}': html.escape(title),
        '{{HEADERS_JS}}': headers_js,
        '{{RAW_DATA_JS}}': raw_data_js,
        '{{FORMATTED_DATA_JS}}': formatted_data_js,
        '{{ENTRY_COUNT}}': str(len(df)),
        '{{SOURCE_LANG}}': dataset.source_lang,
        '{{TARGET_LANG}}': target_lang,
        '{{WORD_COUNT}}': f"{target_word_count:,}",
        '{{CLEAN_TITLE}}': html.escape(title.replace(' ', '_')) # Not currently used
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result

def generate_bulk_visualizer_html(dataset, original_filename=None):
    """Generate Visualizer HTML for bulk generation (Without Occurrences column)"""
    print("IN GENERATE BULK")
    template = load_template()
    print("AFTER LOADING BULK TEMPLATE???")


    df = dataset.to_dataframe()
    print(f"BULK: {df.columns}")
    target_lang = dataset.target_lang or "Target"

    target_word_count = 0
    if target_lang in df.columns:
        target_word_count = df[target_lang].dropna().astype(str).apply(lambda x: len(x.split())).sum()

    if original_filename:
        title = f"{original_filename} Visualizer - {target_lang}"
    else:
        title = f"StringZ Visualizer - {target_lang} Translation Review"

    print(f"Source Lang: {dataset.source_lang}")
    print(f"Target lang: {target_lang}")
    is_chinese_mode = (
        dataset.source_lang == 'CN' and
        'EN' in df.columns and
        target_lang in ['CNTraditional', 'CNSimplified'] 
    )

    # IMPORTANT DIFFERENT FROM STANDARD VISUALIZER - No Occurrences for bulk!
    if is_chinese_mode:
        print("YES CHINESE MODE")
        headers = ["strId", "CN", "EN", target_lang, "State", "Notes"]
        raw_data_rows, formatted_data_rows = _prepare_chinese_bulk_data_rows(df, dataset, target_lang)
    else:
        headers = ["strId", dataset.source_lang, target_lang, "State", "Notes"]

        # Parse data rows without Occurrences
        raw_data_rows, formatted_data_rows = _prepare_bulk_data_rows(df, dataset, target_lang)

    headers_js = '[' + ', '.join(f'"{h}"' for h in headers) + ']'
    print(f"Headers: {headers_js}")
    raw_data_js = _python_list_to_js_array(raw_data_rows)
    formatted_data_js = _python_list_to_js_array(formatted_data_rows)

    # Replace placeholders
    replacements = {
        '{{TITLE}}': html.escape(title),
        '{{HEADERS_JS}}': headers_js,
        '{{RAW_DATA_JS}}': raw_data_js,
        '{{FORMATTED_DATA_JS}}': formatted_data_js,
        '{{ENTRY_COUNT}}': str(len(df)),
        '{{SOURCE_LANG}}': dataset.source_lang,
        '{{TARGET_LANG}}': target_lang,
        '{{WORD_COUNT}}': f"{target_word_count:,}",
        '{{CLEAN_TITLE}}': html.escape(title.replace(' ', '_'))
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template

def _prepare_chinese_data_rows(df, dataset, target_lang):
    """Prepare raw and formatted data rows for Chinese Visualizer (CN - EN - CNTraditional)"""
    raw_data_rows = []
    formatted_data_rows = []

    for idx, (_, row) in enumerate(df.iterrows()):
        str_id_col = dataset.str_id_col or 'strId'
        str_id = str(row.get(str_id_col, ''))

        cn_col = 'CN' if 'CN' in df.columns else 'base'
        cn_text = str(row.get(cn_col, ''))
        en_text = str(row.get('EN', ''))
        target_text = str(row.get(target_lang, '')) if target_lang in df.columns else ''

        occurrences_raw = row.get('Occurrences')
        occurrences = int(occurrences_raw) if occurrences_raw is not None else 1

        raw_cn, formatted_cn = format_text_for_visualizer(cn_text)
        raw_en, formatted_en = format_text_for_visualizer(en_text)
        raw_target, formatted_target = format_text_for_visualizer(target_text)

        raw_row = [str_id, raw_cn, raw_en, raw_target, str(occurrences), "", ""]
        formatted_row = [
            html.escape(str_id),
            formatted_cn,
            formatted_en,
            formatted_target,
            str(occurrences),
            "",
            ""
        ]

        raw_data_rows.append(raw_row)
        formatted_data_rows.append(formatted_row)

    return raw_data_rows, formatted_data_rows

def _prepare_data_rows(df, dataset, target_lang):
    """Prepare raw and formatted data rows for the visualizer"""
    raw_data_rows = []
    formatted_data_rows = []

    # DEBUG
    print("DataFrame columns:", df.columns.tolist())
    
    for idx, (_,row) in enumerate(df.iterrows()):
        # Extract values
        str_id_col = dataset.str_id_col or 'strId'
        str_id = str(row.get(str_id_col, ''))
        en_text = str(row.get(dataset.source_lang, ''))
        target_text = str(row.get(target_lang, '')) if target_lang in df.columns else ''

        # DEBUG occurrences
        occurrences_raw = row.get('Occurrences')
        # print(f"Row {idx}: Occurrences raw = {occurrences_raw}, type = {type(occurrences_raw)}")
        # occurrences = int(row.get('Occurrences', 1))
        occurrences = int(occurrences_raw) if occurrences_raw is not None else 1
        
        # Format text for both views
        raw_en, formatted_en = format_text_for_visualizer(en_text)
        raw_target, formatted_target = format_text_for_visualizer(target_text)
        
        # Create data rows
        raw_row = [str_id, raw_en, raw_target, str(occurrences), "", ""]
        formatted_row = [
            html.escape(str_id),
            formatted_en,
            formatted_target,
            str(occurrences),
            "",
            ""
        ]
        
        raw_data_rows.append(raw_row)
        formatted_data_rows.append(formatted_row)
    
    return raw_data_rows, formatted_data_rows

def _prepare_chinese_bulk_data_rows(df, dataset, target_lang):
    """Prepare data rows for Chinese bulk visualizer (Without Occurrences column)"""
    raw_data_rows = []
    formatted_data_rows = []

    for idx, (_, row) in enumerate(df.iterrows()):
        str_id_col = dataset.str_id_col or 'strId'
        str_id = str(row.get(str_id_col, ''))

        cn_text = str(row.get('CN', ''))
        en_text = str(row.get('EN', ''))
        target_text = str(row.get(target_lang, '')) if target_lang in df.columns else ''

        raw_cn, formatted_cn = format_text_for_visualizer(cn_text)
        raw_en, formatted_en =format_text_for_visualizer(en_text)
        raw_target, formatted_target =format_text_for_visualizer(target_text)

        raw_row = [str_id, raw_cn, raw_en, raw_target, "", ""]
        formatted_row =[
            html.escape(str_id),
            formatted_cn,
            formatted_en,
            formatted_target,
            "",
            ""
        ]

        raw_data_rows.append(raw_row)
        formatted_data_rows.append(formatted_row)

    return raw_data_rows, formatted_data_rows

def _prepare_bulk_data_rows(df, dataset, target_lang):
    """Prepare data rows for bulk visualizer (without Occurrences column)"""
    raw_data_rows = []
    formatted_data_rows = []

    for idx, (_, row) in enumerate(df.iterrows()):
        str_id_col = dataset.str_id_col or 'strId'
        str_id = str(row.get(str_id_col, ''))
        str_id = str(row.get('strId', ''))
        en_text = str(row.get(dataset.source_lang, ''))
        target_text = str(row.get(target_lang, '')) if target_lang in df.columns else ''

        raw_en, formatted_en = format_text_for_visualizer(en_text)
        raw_target, formatted_target = format_text_for_visualizer(target_text)

        # Create data WITHOUT Occurrences
        raw_row = [str_id, raw_en, raw_target, "", ""]
        formatted_row = [
            html.escape(str_id),
            formatted_en,
            formatted_target,
            "", # State
            ""  # Notes
        ]

        raw_data_rows.append(raw_row)
        formatted_data_rows.append(formatted_row)

    return raw_data_rows, formatted_data_rows

def _python_list_to_js_array(data_rows):
    """Convert Python list to JavaScript array format"""
    js_rows = []
    for row in data_rows:
        escaped_row = []
        for item in row:
            if isinstance(item, str):
                # Escape for JavaScript
                escaped = item.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                escaped_row.append(f'"{escaped}"')
            else:
                escaped_row.append(f'"{str(item)}"')
        js_rows.append('[' + ', '.join(escaped_row) + ']')
    
    return '[' + ', '.join(js_rows) + ']'
