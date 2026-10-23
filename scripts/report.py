#!/usr/bin/env python3
"""Weekly GitHub Trending + MCP/RAG/Skills discovery report.

Trending weekly stars are read from the Trending HTML. Repository Search returns
cumulative stars; week-over-week changes are calculated only from saved snapshots.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'reports'
SNAPSHOT = REPORTS / 'star_snapshots.json'
CONFIG = ROOT / 'config' / 'topics.json'
BASE = 'https://github.com'
SOURCES = [('Overall', '/trending?since=weekly'), ('Python', '/trending/python?since=weekly'), ('TypeScript', '/trending/typescript?since=weekly')]
DEFAULT_TOPICS = {
    'AI Agent': ['agent', 'agentic', 'multi-agent', 'autonomous', 'coding assistant', 'agent harness'],
    'LLM': ['llm', 'large language model', 'language model', 'transformer', 'fine-tun', 'vllm', 'llm inference'],
    'MCP': ['model context protocol', 'mcp-server', 'mcp server', 'mcp-client', 'mcp client', 'mcp registry'],
    'RAG': ['retrieval augmented generation', 'retrieval-augmented-generation', 'agentic rag', 'graphrag', 'rag pipeline'],
    'Skills': ['agent skills', 'agent-skills', 'skill.md', 'claude skills', 'codex skills'],
}
SEARCHES = {
    'MCP': 'topic:model-context-protocol',
    'RAG': 'topic:retrieval-augmented-generation',
    'Skills': 'topic:agent-skills',
}
HEADERS = {'User-Agent': 'GitHub-Trend-Monitor/2.0', 'Accept': 'text/html'}
API_HEADERS = {'User-Agent': 'GitHub-Trend-Monitor/2.0', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
if os.getenv('GITHUB_TOKEN'):
    API_HEADERS['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']


def load_config():
    if not CONFIG.exists():
        return {'topics': DEFAULT_TOPICS, 'top_n': 15, 'search_per_topic': 20}
    obj = json.loads(CONFIG.read_text(encoding='utf-8'))
    return {'topics': obj.get('topics', DEFAULT_TOPICS), 'top_n': max(1, int(obj.get('top_n', 15))), 'search_per_topic': min(50, max(1, int(obj.get('search_per_topic', 20))))}


def weekly_number(text):
    # IMPORTANT: only parse numbers immediately paired with "stars this week".
    match = re.search(r'([\d,]+)\s+stars?\s+this\s+week', text, flags=re.I)
    return int(match.group(1).replace(',', '')) if match else None


def fetch_trending(session, category, route):
    response = session.get(BASE + route, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    result = []
    for article in soup.select('article.Box-row'):
        anchor = article.select_one('h2 a[href]')
        if not anchor:
            continue
        repo = '/'.join(anchor['href'].strip('/').split('/')[:2])
        if len(repo.split('/')) != 2:
            continue
        desc_el = article.select_one('p')
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        # Read the entire "stars this week" sentence, not arbitrary other span numbers.
        weekly = weekly_number(article.get_text(' ', strip=True))
        result.append({
            'repo': repo, 'url': BASE + '/' + repo,
            'description': desc_el.get_text(' ', strip=True) if desc_el else '',
            'language': lang_el.get_text(' ', strip=True) if lang_el else '',
            'weekly': weekly, 'total': None, 'sources': [category], 'topics': [],
        })
    if not result:
        raise RuntimeError('未解析到项目（GitHub Trending 页面结构可能已变化）')
    return result


def search_topic(session, category, query, size):
    response = session.get('https://api.github.com/search/repositories', headers=API_HEADERS,
                           params={'q': query, 'sort': 'stars', 'order': 'desc', 'per_page': size}, timeout=30)
    response.raise_for_status()
    result = []
    for x in response.json().get('items', []):
        result.append({
            'repo': x['full_name'], 'url': x['html_url'],
            'description': x.get('description') or '', 'language': x.get('language') or '',
            'weekly': None, 'total': x.get('stargazers_count'),
            'sources': ['Search:' + category], 'topics': x.get('topics') or [],
        })
    return result


def merge(rows):
    unique = {}
    for x in rows:
        key = x['repo'].lower()
        if key not in unique:
            unique[key] = dict(x)
            continue
        old = unique[key]
        old['sources'] = sorted(set(old['sources'] + x['sources']))
        old['topics'] = sorted(set(old['topics'] + x['topics']))
        if old['weekly'] is None and x['weekly'] is not None:
            old['weekly'] = x['weekly']
        if x['total'] is not None:
            old['total'] = x['total']
        if len(x['description']) > len(old['description']):
            old['description'] = x['description']
        if not old['language']:
            old['language'] = x['language']
    return list(unique.values())


def classify(row, keywords):
    haystack = (row['repo'] + ' ' + row['description']).lower()
    tags = [t.lower() for t in row['topics']]
    match = set()
    for name, terms in keywords.items():
        if any(term.lower() in haystack or term.lower() in tags for term in terms):
            match.add(name)
    for src in row['sources']:
        if src.startswith('Search:'):
            match.add(src[len('Search:'):] if src.startswith('Search:') else src)
    return match


def load_snapshots():
    try:
        obj = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        return obj if isinstance(obj, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def update_snapshots(rows, now):
    """Compare consecutive observations; gap may not be exactly seven days."""
    history = load_snapshots()
    day = now.date().isoformat()
    previous_dates = sorted(d for d in history if d < day)
    previous_day = previous_dates[-1] if previous_dates else None
    previous = history.get(previous_day, {}) if previous_day else {}
    for row in rows:
        if row['total'] is None or row['repo'] not in previous:
            row['snapshot_growth'] = None
        else:
            diff = row['total'] - previous[row['repo']]
            row['snapshot_growth'] = diff if diff >= 0 else None
    today = dict(history.get(day, {}))
    today.update({x['repo']: x['total'] for x in rows if x['total'] is not None})
    history[day] = today
    # Bound snapshot file size while retaining 12 months of weekly observations.
    history = {k: history[k] for k in sorted(history)[-60:]}
    SNAPSHOT.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return previous_day


def sort_rows(rows):
    # A real Trending weekly value outranks snapshots / unknown weekly growth.
    return sorted(rows, key=lambda x: (x['weekly'] is not None, x['weekly'] or -1,
                                      x['snapshot_growth'] is not None, x['snapshot_growth'] or -1,
                                      x['total'] or -1), reverse=True)


def clean(value):
    return ' '.join(str(value or '').replace('|', ' / ').split()).replace('[', '［').replace(']', '］')


def write_report(rows, errors, now, previous_day, config):
    lines = [
        '# GitHub 技术趋势周报', '',
        '生成时间：' + now.strftime('%Y-%m-%d %H:%M UTC'), '',
        '数据来源：GitHub Trending Weekly + GitHub Repository Search API。',
        '指标说明：**Trending 本周新增 Stars**来自 Trending 网页；**API 累计 Stars**不是周增量。',
        '快照变化＝当前累计 Stars－上次采集的累计 Stars（可能不是严格七天）。',
        '没有历史快照的项目显示“—”，不得将累计 Stars 当成周增量。',
        '主题分类包含关键词和 Topic 检索；同一项目可出现在多个分类。',
        '上次快照日期：' + (previous_day or '无（首次运行）'), '',
    ]
    top = config['top_n']
    sections = [('本周热门总榜', lambda r: 'Overall' in r['sources'])]
    for name, terms in config['topics'].items():
        sections.append((name, lambda r, name=name: name in r['categories']))
    for name in ('Python', 'TypeScript'):
        sections.append((name, lambda r, name=name: r['language'].lower() == name.lower() or name in r['sources']))
    for title, predicate in sections:
        selected = sort_rows([r for r in rows if predicate(r)])[:top]
        lines += [f'## {title}', '', '| 项目 | 语言 | Trending 本周新增 Stars | API 累计 Stars | 快照变化 | 项目简介 |', '|---|---|---:|---:|---:|---|']
        for x in selected:
            star = f"{x['weekly']:,}" if x['weekly'] is not None else '—'
            total = f"{x['total']:,}" if x['total'] is not None else '—'
            delta = f"{x['snapshot_growth']:+,}" if x['snapshot_growth'] is not None else '—'
            lines.append(f"| [{clean(x['repo'])}]({x['url']}) | {clean(x['language']) or '—'} | {star} | {total} | {delta} | {clean(x['description']) or '—'} |")
        if not selected:
            lines.append('| 暂无匹配项目 | — | — | — | — | — |')
        lines.append('')
    if errors:
        lines += ['## 采集警告', ''] + [f'- {clean(err)}' for err in errors] + ['']
    content = '\n'.join(lines) + '\n'
    (REPORTS / (now.date().isoformat() + '.md')).write_text(content, encoding='utf-8')
    (ROOT / 'LATEST.md').write_text(content, encoding='utf-8')


def main():
    config = load_config()
    session = requests.Session()
    rows, errors = [], []
    for name, route in SOURCES:
        try:
            rows += fetch_trending(session, name, route)
            print(f'Trending {name}: OK')
        except (requests.RequestException, RuntimeError) as exc:
            errors.append(f'Trending {name}: {exc}')
    for name, query in SEARCHES.items():
        try:
            found = search_topic(session, name, query, config['search_per_topic'])
            rows += found
            print(f'Search {name}: {len(found)} repos')
        except (requests.RequestException, ValueError, KeyError) as exc:
            errors.append(f'Search {name}: {exc}')
    if not rows:
        raise RuntimeError('所有来源均采集失败：' + '; '.join(errors))
    unique = merge(rows)
    for row in unique:
        row['categories'] = classify(row, config['topics'])
    now = datetime.now(timezone.utc)
    REPORTS.mkdir(parents=True, exist_ok=True)
    previous_day = update_snapshots(unique, now)
    write_report(unique, errors, now, previous_day, config)
    print(f'Wrote reports/{now.date().isoformat()}.md and LATEST.md ({len(unique)} unique repos)')
    for err in errors:
        print('WARNING:', err)


if __name__ == '__main__':
    main()
