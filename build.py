#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Markdown 源文件转换为 HTML 页面。
直接读取上级目录中的 01_第一天.md ~ 06_第六天.md，生成 day1.html ~ day6.html。
"""
import re, os, html as html_mod

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

DAY_META = [
    {"file": "01_第一天.md", "title": "第一天", "subtitle": "\u201c他们\u201d都曾是\u201c别人家的孩子\u201d", "out": "day1.html", "num": 1},
    {"file": "02_第二天.md", "title": "第二天", "subtitle": "\u201c他们\u201d都在用生命进谏", "out": "day2.html", "num": 2},
    {"file": "03_第三天.md", "title": "第三天", "subtitle": "\u201c他们\u201d都因正直而遭遇不公", "out": "day3.html", "num": 3},
    {"file": "04_第四天.md", "title": "第四天", "subtitle": "\u201c他们\u201d是真正的\u201c父母官\u201d", "out": "day4.html", "num": 4},
    {"file": "05_第五天.md", "title": "第五天", "subtitle": "\u201c他们\u201d都遭遇了\u201c奸臣\u201d当道", "out": "day5.html", "num": 5},
    {"file": "06_第六天.md", "title": "第六天", "subtitle": "\u201c他们\u201d都置于\u201c以德服人\u201d", "out": "day6.html", "num": 6},
]

def clean_latex(text):
    """清除 LaTeX 残留标记"""
    # Remove $ ^{*} $ markers
    text = re.sub(r'\$\s*\^\{\*\}\s*\$', '', text)
    # Remove $\underset{\cdot}{X}$ -> X (with emphasis dot)
    text = re.sub(r'\$\s*\\underset\{\\cdot\}\{([^}]+)\}\s*\$', r'<span class="em-dot">\1</span>', text)
    # Remove remaining $ ... $
    text = re.sub(r'\$[^$]*\$', '', text)
    # Remove ★ $ ^{⑩} $ style
    text = re.sub(r'\$\s*\\underset\{[^}]*\}\{[^}]*\}\s*\$', '', text)
    # Clean up ^{...} patterns
    text = re.sub(r'\^\{[^}]*\}', '', text)
    return text.strip()

def escape_html(text):
    """HTML escape but preserve our tags"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text

def process_inline(text):
    """Process inline formatting: bold, etc."""
    text = clean_latex(text)
    # Handle **bold**
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text

def parse_day(filepath):
    """Parse a day's markdown file into structured sections."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove \r
    content = content.replace('\r', '')
    lines = content.split('\n')
    
    # Split into passages and translations
    sections = []
    current_section = None
    in_translation = False
    translations = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip first two non-empty lines (day title and subtitle)
        if i < 5 and (line.startswith('第') and '天' in line):
            i += 1
            continue
        
        # Translation section
        if ('译文' in line or '课文参考译文' in line or '所有段落详文' in line) and (line.startswith('#') or line.startswith('##')):
            in_translation = True
            if current_section:
                sections.append(current_section)
                current_section = None
            i += 1
            continue
        
        if in_translation:
            # Parse translation items like 【1】...
            m = re.match(r'【(\d+)】(.*)', line)
            if m:
                trans_num = m.group(1)
                trans_text = m.group(2)
                # Gather continuation lines
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('【') or (next_line.startswith('#') and not in_translation):
                        break
                    if next_line:
                        trans_text += next_line
                    i += 1
                translations.append((trans_num, clean_latex(trans_text)))
                continue
            i += 1
            continue
        
        # Detect section headers (## or ### or # with number)
        header_match = re.match(r'^#{1,4}\s*(\d{2})\s+(.+)', line)
        if not header_match:
            header_match = re.match(r'^#{1,4}\s*(\d{1,2})\s+(.+)', line)
        
        if header_match and not line.startswith('####'):
            if current_section:
                sections.append(current_section)
            num = header_match.group(1).lstrip('0') or '0'
            title = header_match.group(2).strip()
            title = clean_latex(title)
            current_section = {
                'num': num,
                'title': title,
                'lines': []
            }
            i += 1
            continue
        
        if current_section is not None:
            current_section['lines'].append(lines[i])
        
        i += 1
    
    if current_section:
        sections.append(current_section)
    
    return sections, translations

def render_section(section):
    """Render a passage section to HTML."""
    out = []
    num = section['num']
    title = process_inline(section['title'])
    
    out.append(f'<div class="passage" id="p{num}">')
    out.append(f'  <h2 class="passage-title"><span class="passage-num">{num.zfill(2)}</span> {title}</h2>')
    
    lines = section['lines']
    # Find blocks: original text (first big paragraph), notes (①②...), key sentences (* ...), word details
    
    # State machine
    original_text = []
    notes = []
    key_sentences = []
    word_blocks = []
    current_word_block = None
    
    state = 'original'  # original, notes, key, words
    
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        
        # Clean LaTeX
        cleaned = clean_latex(line)
        
        # Skip pure header lines that are sub-headers for word explanations
        if re.match(r'^#{1,4}\s*\*', line) or re.match(r'^#{1,4}\s*\$', line):
            state = 'key'
            # Extract key sentence
            key_text = re.sub(r'^#{1,4}\s*\*?\s*', '', line)
            key_text = clean_latex(key_text)
            key_text = process_inline(key_text)
            if key_text.strip():
                key_sentences.append(key_text)
            continue
        
        # Key sentence line starting with * or $ ^{*} $
        if line.startswith('* ') or line.startswith('$ ^{*} $') or line.startswith('$^{*}$'):
            state = 'key'
            key_text = re.sub(r'^\*\s*', '', line)
            key_text = re.sub(r'^\$\s*\^\{\*\}\s*\$\s*', '', key_text)
            key_text = clean_latex(key_text)
            key_text = process_inline(key_text)
            if key_text.strip():
                key_sentences.append(key_text)
            continue
        
        # Word definition lines: N.<类型>内容
        word_match = re.match(r'^(\d+)\.\s*[<＜]([^>＞]+)[>＞]\s*(.*)', cleaned)
        if word_match:
            state = 'words'
            pos = word_match.group(2)
            definition = word_match.group(3)
            current_word_block = {'pos': pos, 'def': process_inline(definition), 'examples': []}
            word_blocks.append(current_word_block)
            continue
        
        # Standalone pos tag without number (for 笃, 贻 etc.)
        pos_match = re.match(r'^[<＜]([^>＞]+)[>＞]\s*(.*)', cleaned)
        if pos_match and state in ('key', 'words', 'notes'):
            state = 'words'
            pos = pos_match.group(1)
            definition = pos_match.group(2)
            current_word_block = {'pos': pos, 'def': process_inline(definition), 'examples': []}
            word_blocks.append(current_word_block)
            continue
        
        # Pronunciation hints like wú, wáng, zhòng etc.
        if re.match(r'^[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]+$', cleaned) and len(cleaned) < 12:
            continue
        
        # Note lines: ①②③... or ★①...
        note_match = re.match(r'^(☑)?[★✦]?\s*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚]', cleaned)
        if note_match:
            state = 'notes'
            is_key = '★' in line or '☑' in line
            note_text = cleaned
            note_text = re.sub(r'^☑\s*', '', note_text)
            note_text = re.sub(r'^★\s*', '', note_text)
            note_text = process_inline(note_text)
            notes.append({'text': note_text, 'key': is_key})
            continue
        
        # Example lines (《...》 pattern in word detail context)
        if state == 'words' and current_word_block is not None:
            if '《' in cleaned and '》' in cleaned and '：' in cleaned:
                current_word_block['examples'].append({'source': process_inline(cleaned), 'trans': ''})
                continue
            if cleaned.startswith('译文') or cleaned.startswith('译文：'):
                trans = re.sub(r'^译文[：:]?\s*', '', cleaned)
                trans = process_inline(trans)
                if current_word_block['examples']:
                    current_word_block['examples'][-1]['trans'] = trans
                continue
            # Continuation of translation
            if current_word_block['examples'] and not current_word_block['examples'][-1]['trans']:
                # Might be continuation of source
                if '《' not in cleaned and not re.match(r'^\d+\.', cleaned):
                    last_ex = current_word_block['examples'][-1]
                    last_ex['source'] += process_inline(cleaned)
                    continue
            elif current_word_block['examples'] and current_word_block['examples'][-1]['trans']:
                # Continuation of translation text
                if not re.match(r'^\d+\.', cleaned) and '《' not in cleaned:
                    last_ex = current_word_block['examples'][-1]
                    last_ex['trans'] += process_inline(cleaned)
                    continue
        
        # Original text (the main paragraph - typically the first substantial text block)
        if state == 'original':
            cleaned_proc = process_inline(cleaned)
            if cleaned_proc:
                original_text.append(cleaned_proc)
            continue
        
        # Catch uncategorized lines as continuation of notes or original
        if state == 'notes' and notes:
            notes[-1]['text'] += process_inline(cleaned)
        elif state == 'key' and key_sentences:
            key_sentences[-1] += process_inline(cleaned)
    
    # Render original text
    if original_text:
        # Extract source reference
        source_ref = ''
        main_text = []
        for t in original_text:
            src_match = re.search(r'[（(]节选自[《]?(.+?)[》]?[）)]', t)
            if src_match:
                source_ref = src_match.group(0)
                t_clean = t.replace(source_ref, '').strip()
                if t_clean:
                    main_text.append(t_clean)
            else:
                main_text.append(t)
        
        full_text = ''.join(main_text)
        out.append(f'  <div class="original-text">{full_text}')
        if source_ref:
            source_ref = process_inline(source_ref)
            out.append(f'    <span class="source">{source_ref}</span>')
        out.append('  </div>')
    
    # Render notes
    if notes:
        out.append('  <div class="notes">')
        for note in notes:
            cls = ' note-key' if note['key'] else ''
            star = '<span class="note-star">★</span>' if note['key'] else ''
            out.append(f'    <div class="note{cls}">{star}{note["text"]}</div>')
        out.append('  </div>')
    
    # Render key sentences
    for ks in key_sentences:
        if ks.strip():
            out.append(f'  <div class="key-sentence">{ks}</div>')
    
    # Render word details
    if word_blocks:
        out.append('  <div class="word-detail">')
        out.append('    <div class="word-detail-title">字词详解</div>')
        for wb in word_blocks:
            out.append('    <div class="word-meaning">')
            out.append(f'      <span class="word-pos">{wb["pos"]}</span>')
            out.append(f'      <span class="word-def">{wb["def"]}</span>')
            for ex in wb['examples']:
                out.append('      <div class="word-example">')
                out.append(f'        <span class="example-source">{ex["source"]}</span>')
                if ex['trans']:
                    out.append(f'        <span class="example-trans">{ex["trans"]}</span>')
                out.append('      </div>')
            out.append('    </div>')
        out.append('  </div>')
    
    out.append('</div>')
    return '\n'.join(out)

def render_translations(translations):
    """Render translations section."""
    if not translations:
        return ''
    out = []
    out.append('<div class="translations">')
    out.append('  <h2 class="translations-title">译文</h2>')
    for num, text in translations:
        out.append(f'  <div class="trans-item">')
        out.append(f'    <span class="trans-num">{num}</span>')
        out.append(f'    <span class="trans-text">{text}</span>')
        out.append(f'  </div>')
    out.append('</div>')
    return '\n'.join(out)

def generate_page(meta):
    """Generate a complete HTML page for a day."""
    filepath = os.path.join(SRC_DIR, meta['file'])
    sections, translations = parse_day(filepath)
    
    num = meta['num']
    prev_link = f'day{num-1}.html' if num > 1 else None
    next_link = f'day{num+1}.html' if num < 6 else None
    
    # Build TOC
    toc_items = []
    for sec in sections:
        toc_items.append(f'<a href="#p{sec["num"]}">{sec["num"].zfill(2)} {sec["title"]}</a>')
    toc_html = '\n      '.join(toc_items)
    
    # Build sections
    sections_html = '\n\n'.join(render_section(sec) for sec in sections)
    
    # Build translations
    trans_html = render_translations(translations)
    
    # Build nav
    nav_parts = []
    if prev_link:
        nav_parts.append(f'<a href="{prev_link}">← 上一天</a>')
    else:
        nav_parts.append('<span></span>')
    nav_parts.append('<a href="index.html" class="nav-home">目录</a>')
    if next_link:
        nav_parts.append(f'<a href="{next_link}">下一天 →</a>')
    else:
        nav_parts.append('<span></span>')
    nav_html = '\n    '.join(nav_parts)
    
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta["title"]} · 21天古文拆分</title>
  <meta name="description" content="{meta["title"]} - {meta["subtitle"]}">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <h1 class="page-title">{meta["title"]}</h1>
    <p class="page-subtitle">{meta["subtitle"]}</p>

    <div class="toc">
      <div class="toc-title">本日篇目</div>
      {toc_html}
    </div>

    {sections_html}

    {trans_html}

    <div class="page-nav">
      {nav_html}
    </div>

    <div class="site-footer">
      <p>21天古文拆分 · 前六天校对版</p>
    </div>
  </div>
</body>
</html>'''
    
    outpath = os.path.join(OUT_DIR, meta['out'])
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'Generated: {meta["out"]}')

if __name__ == '__main__':
    for meta in DAY_META:
        generate_page(meta)
    print('Done! All 6 pages generated.')
