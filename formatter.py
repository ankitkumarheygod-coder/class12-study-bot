import re

def clean_latex_and_markdown(text: str) -> str:
    if not text:
        return ""
    
    # 1. Remove Markdown Bold and make it UPPERCASE
    text = re.sub(r'\*\*(.*?)\*\*', lambda m: m.group(1).upper(), text)
    
    # 2. Remove Markdown Italics
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # 3. Remove Headings (### Heading -> HEADING)
    text = re.sub(r'^#+\s*(.*)$', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    
    # 4. LaTeX Fractions: \frac{a}{b} -> (a)/(b)
    while r'\frac' in text:
        text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1)/(\2)', text)
    
    # 5. Greek Letters & Math Symbols
    replacements = {
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ', r'\Delta': 'Δ',
        r'\theta': 'θ', r'\pi': 'π', r'\sigma': 'σ', r'\omega': 'ω', r'\Omega': 'Ω',
        r'\lambda': 'λ', r'\mu': 'μ', r'\rho': 'ρ', r'\epsilon': 'ε',
        r'\times': '×', r'\div': '÷', r'\pm': '±', r'\leq': '≤', r'\geq': '≥',
        r'\neq': '≠', r'\approx': '≈', r'\propto': '∝', r'\infty': '∞',
        r'\sqrt': '√', r'\cdot': '·', r'\rightarrow': '→', r'\Rightarrow': '⇒'
    }
    for latex, unicode_char in replacements.items():
        text = text.replace(latex, unicode_char)
        
    # 6. Superscripts (x^2 -> x²)
    superscripts = {'0':'⁰', '1':'¹', '2':'²', '3':'³', '4':'⁴', '5':'⁵', '6':'⁶', '7':'⁷', '8':'⁸', '9':'⁹', '+': '⁺', '-': '⁻'}
    def replace_super(match):
        content = match.group(1)
        return ''.join(superscripts.get(c, '^'+c) for c in content)
    
    text = re.sub(r'\^\{([^}]+)\}', replace_super, text)
    text = re.sub(r'\^([0-9])', replace_super, text)
    
    # 7. Subscripts (x_2 -> x₂)
    subscripts = {'0':'₀', '1':'₁', '2':'₂', '3':'₃', '4':'₄', '5':'₅', '6':'₆', '7':'₇', '8':'₈', '9':'₉'}
    def replace_sub(match):
        content = match.group(1)
        return ''.join(subscripts.get(c, '_'+c) for c in content)
        
    text = re.sub(r'_\{([^}]+)\}', replace_sub, text)
    text = re.sub(r'_([0-9])', replace_sub, text)
    
    # 8. Remove remaining $ signs used for math blocks
    text = text.replace('$', '')
    
    return text.strip()

def split_message(text: str, max_length: int = 4000) -> list:
    """Splits a long message into chunks at paragraph or sentence boundaries."""
    if len(text) <= max_length:
        return [text]
        
    chunks = []
    while len(text) > max_length:
        # Try to split at double newline (paragraph)
        split_index = text.rfind('\n\n', 0, max_length)
        if split_index == -1:
            # Try single newline
            split_index = text.rfind('\n', 0, max_length)
        if split_index == -1:
            # Try full stop
            split_index = text.rfind('. ', 0, max_length)
        if split_index == -1:
            # Hard split
            split_index = max_length
            
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
        
    if text:
        chunks.append(text)
    return chunks
