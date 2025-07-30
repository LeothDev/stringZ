import re
from collections import defaultdict

# Basic Keywords
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
