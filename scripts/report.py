#!/usr/bin/env python3
"""GitHub Trending weekly report. Uses public GitHub Trending pages."""
from datetime import datetime, timezone
from pathlib import Path
import re
import requests
from bs4 import BeautifulSoup

BASE = 'https://github.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TrendMonitor/1.0)', 'Accept': 'text/html'}
SOURCES = [('Overall', '/trending?since=weekly'), ('Python', '/trending/python?since=weekly'), ('TypeScript', '/trending/typescript?since=weekly')]
KEYWORDS = {
    'AI Agent': ['agent', 'agentic', 'multi-agent', 'mcp', 'autonomous', 'computer use', 'coding assistant'],
    'LLM': ['llm', 'large language model', 'language model', 'rag', 'inference', 'transformer', 'fine-tun', 'vllm'],
}

def fetch(category, route):
    response = requests.get(BASE + route, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    entries = []
    for article in soup.select('article.Box-row'):
        anchor = article.select_one('h2 a[href]')
        if not anchor:
            continue
        repo = '/'.join(anchor.get('href','').strip('/').split('/')[:2])
        if len(repo.split('/')) != 2:
            continue
        description_tag = article.select_one('p')
        description = description_tag.get_text(' ', strip=True) if description_tag else ''
        lang_tag = article.select_one('[itemprop="programmingLanguage"]')
        language = lang_tag.get_text(' ', strip=True) if lang_tag else ''
        stars_week = ''
        for span in article.select('span'):
            s = span.get_text(' ',strip=True)
            if 'stars this week' in s.lower():
                match = re.search(r'[\d,]+', s)
                stars_week = match.group(0) if match else ''
                break
        entries.append({'repo':repo, 'url':BASE+'/'+repo, 'description':description.replace('|','\\|'), 'language': language, 'weekly':stars_week, 'source':category})
    if not entries:
        raise RuntimeError(f'No trending repositories parsed for {category}; GitHub may have changed its HTML.')
    return entries

def main():
    all_rows = []
    errors = []
    for name, route in SOURCES:
        try:
            all_rows.extend(fetch(name, route))
        except Exception as exc:
            errors.append(f'{name}: {exc}')
    if not all_rows:
        raise RuntimeError('All sources failed: '+ '; '.join(errors))
    by_repo = {}
    for item in all_rows:
        if item['repo'] not in by_repo:
            by_repo[item['repo']] = dict(item, sources=[item['source']])
        else:
            by_repo[item['repo']]['sources'].append(item['source'])
            if not by_repo[item['repo']]['weekly'] and item['weekly']:
                by_repo[item['repo']]['weekly'] = item['weekly']
    rows = list(by_repo.values())
    lines = ['# GitHub 技术趋势周报', '', f'生成时间：{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', '', '数据来源：GitHub Trending Weekly；“本周新增 Stars”为网页显示值，非累计 Stars。', '说明：主题分组按项目名称和简介匹配关键词，可能遗漏未写明主题的项目。', '']
    sections = [ ('本周热门总榜',lambda x: 'Overall' in x['sources']), ('AI Agent',lambda x: any(k in (x['repo']+' '+x['description']).lower() for k in KEYWORDS['AI Agent'])), ('LLM',lambda x:any(k in (x['repo']+' '+x['description']).lower() for k in KEYWORDS['LLM'])), ('Python',lambda x:x['language'].lower()=='python' or 'Python' in x['sources']), ('TypeScript',lambda x:x['language'].lower()=='typescript' or 'TypeScript' in x['sources'])]
    for name, selector in sections:
        selection=[x for x in rows if selector(x)][:15]
        lines += [f'## {name}', '', '| 项目 | 语言 | 本周新增 Stars | 项目说明 |', '|---|---|---:|---|']
        for x in selection:
            desc=x['description'][:115].replace('\n',' ')
            lines.append(f"| [{x['repo']}]({x['url']}) | {x['language'] or '—'} | {x['weekly'] or '—'} | {desc} |")
        if not selection: lines += ['| 暂无匹配项目 | — | — | — |']
        lines += ['']
    if errors:
        lines += ['## 采集异常','']+[f'- {e}' for e in errors]+['']
    out=Path('reports');out.mkdir(exist_ok=True)
    content='\n'.join(lines)+'\n'
    today=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    (out/f'{today}.md').write_text(content,encoding='utf-8')
    Path('LATEST.md').write_text(content,encoding='utf-8')
    print(f'Wrote reports/{today}.md and LATEST.md ({len(rows)} unique repos)')
if __name__=='__main__':main()
