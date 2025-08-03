import re
from .game_elements import count_enhanced_tokens, detect_malformed_tags

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

