#!/usr/bin/env python3
"""A dependency-free static personal website and Markdown blog. Python 3.11+."""
from __future__ import annotations

import argparse
from datetime import date
from html import escape, unescape
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT / '_site'
CONTENT = ROOT / 'content'

ICONS = {
    'arrow': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'external': '<path d="M14 4h6v6m0-6L10 14"/><path d="M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5"/>',
    'github': '<path d="M9 19c-4 1-4-2-6-2m12 5v-4a3.5 3.5 0 0 0-1-3c3 0 6-1 6-5a4 4 0 0 0-1-3c0-1 0-2-.2-3 0 0-1 0-3 1a11 11 0 0 0-6 0C8 4 7 4 7 4c-.5 1-.5 2-.2 3a4 4 0 0 0-1 3c0 4 3 5 6 5a3.5 3.5 0 0 0-1 3v4"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    'moon': '<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>',
    'menu': '<path d="M4 7h16M4 12h16M4 17h16"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    'book': '<path d="M12 5C8 2 3 4 3 4v15s5-2 9 1c4-3 9-1 9-1V4s-5-2-9 1Zm0 0v15"/>',
    'cap': '<path d="m2 8 10-5 10 5-10 5L2 8Zm4 2v7c4 3 8 3 12 0v-7m4-2v8"/>',
    'pin': '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
    'code': '<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18"/>',
    'rss': '<circle cx="5" cy="19" r="1"/><path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/>',
    'up': '<path d="M12 19V5m-6 6 6-6 6 6"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
}


def icon(name: str, cls: str = '') -> str:
    return f'<svg class="icon {cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'


def e(value) -> str:
    return escape(str(value), quote=True)


def inline(text: str) -> str:
    """Escape HTML first; allow a deliberately small, safe Markdown subset."""
    text = escape(text)
    tokens: list[str] = []

    def stash(value: str) -> str:
        tokens.append(value)
        return f'\x00{len(tokens) - 1}\x00'

    def emphasis(value: str) -> str:
        value = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
        return re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', value)

    text = re.sub(r'`([^`]+)`', lambda m: stash(f'<code>{m[1]}</code>'), text)

    def link(match):
        label, raw = match.groups()
        # Decode only the URL (for scheme checking), then escape it exactly
        # once. The label stays HTML-escaped; unescaping it would reintroduce
        # raw markup from the source.
        url = unescape(raw)
        parsed = urlsplit(url)
        if parsed.scheme and parsed.scheme not in ('https', 'http', 'mailto'):
            return label
        if url.startswith('//'):
            return label
        # Both the label and URL may contain protected code tokens. Resolve
        # those first, then format emphasis inside the label.
        label, url = resolve_tokens(label), resolve_tokens(url)
        return stash(f'<a href="{e(url)}">{emphasis(label)}</a>')

    def resolve_tokens(value: str) -> str:
        for _ in range(16):
            if '\x00' not in value:
                break
            value = re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], value)
        else:
            raise ValueError('Unresolved inline Markdown token')
        return value

    # Allow one level of balanced parentheses inside URLs. Brackets inside a
    # code span can stay in the label.
    text = re.sub(r'\[([^\[\]]*)\]\(((?:[^()]|\([^()]*\))*)\)', link, text)
    text = emphasis(text)
    # Links are protected as tokens, so resolve all remaining tokens here.
    return resolve_tokens(text)


def markdown(source: str):
    lines = source.splitlines()
    output, toc = [], []
    i = 0
    special = re.compile(r'^(#{1,4}\s|```|>\s?|[-*]\s|\d+\.\s|---\s*$)')
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            lang = re.sub(r'[^a-zA-Z0-9_+-]', '', line[3:].strip())
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError('Unclosed code fence')
            output.append(f'<div class="code-block"><div class="code-caption"><span>{e(lang or "text")}</span></div><pre><code>{escape(chr(10).join(code))}</code></pre></div>')
            i += 1
            continue
        heading = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading:
            level = max(2, len(heading[1]))
            anchor = f'section-{len(toc) + 1}'
            toc.append((anchor, heading[2], level))
            output.append(f'<h{level} id="{anchor}">{inline(heading[2])}</h{level}>')
            i += 1
            continue
        if re.match(r'^---\s*$', line):
            output.append('<hr>')
            i += 1
            continue
        if line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                quote_lines.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            output.append('<blockquote><p>' + inline(' '.join(quote_lines)) + '</p></blockquote>')
            continue
        list_match = re.match(r'^([-*]|\d+\.)\s+(.+)', line)
        if list_match:
            ordered = list_match[1][0].isdigit()
            pattern = r'^\d+\.\s+(.+)' if ordered else r'^[-*]\s+(.+)'
            tag = 'ol' if ordered else 'ul'
            items = []
            while i < len(lines) and (item := re.match(pattern, lines[i])):
                items.append('<li>' + inline(item[1]) + '</li>')
                i += 1
            output.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not special.match(lines[i]):
            para.append(lines[i])
            i += 1
        output.append('<p>' + inline(' '.join(para)) + '</p>')
    return '\n'.join(output), toc


def load_content():
    profile = json.loads((CONTENT / 'profile.json').read_text(encoding='utf-8'))
    if not re.fullmatch(r'[A-Za-z0-9-]+', profile['github_username']):
        raise ValueError('Invalid GitHub username')
    base = urlsplit(profile['site_url'])
    if base.scheme != 'https' or not base.netloc or base.query or base.fragment or base.path not in ('', '/'):
        raise ValueError('site_url must be an HTTPS site root without a path, query, or fragment')
    posts, slugs = [], set()
    for path in sorted((CONTENT / 'posts').glob('*.md')):
        text = path.read_text(encoding='utf-8')
        parts = text.split('+++', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f'{path.name}: missing +++ TOML header')
        meta = tomllib.loads(parts[1])
        for key in ('title', 'date', 'slug', 'summary', 'tags'):
            if key not in meta:
                raise ValueError(f'{path.name}: missing {key}')
        slug = meta['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or slug in slugs:
            raise ValueError(f'{path.name}: invalid or duplicate slug')
        slugs.add(slug)
        day = date.fromisoformat(str(meta['date']))
        if not isinstance(meta['tags'], list) or not all(isinstance(t, str) and t.strip() for t in meta['tags']):
            raise ValueError(f'{path.name}: tags must be an array of nonempty strings')
        rendered, toc = markdown(parts[2].strip())
        chars = len(re.findall(r'[\u4e00-\u9fff]|[A-Za-z0-9_]+', parts[2]))
        posts.append(dict(meta, date=day.isoformat(), body=rendered, toc=toc,
                          source=parts[2], minutes=max(1, round(chars / 350))))
    posts.sort(key=lambda p: (-date.fromisoformat(p['date']).toordinal(), p['slug']))
    return profile, posts


def layout(profile, title, body, *, prefix='', active='home', path='', description='', article=False):
    name = profile['name']
    page_title = f'{title} · {name}' if title else f'{name} · 个人主页与博客'
    base = profile['site_url'].rstrip('/')
    canonical = base + '/' + path
    github = 'https://github.com/' + profile['github_username']
    description = description or profile['description']
    home = prefix + 'index.html'
    blog = prefix + 'blog/index.html'
    nav_items = [('home', home, '首页'), ('about', home + '#about', '关于'),
                 ('education', home + '#education', '教育'), ('projects', home + '#projects', '实践'), ('blog', blog, '博客')]
    nav = ''.join(f'<a href="{href}"' + (' class="active" aria-current="page"' if key == active else '') + f'>{label}</a>' for key, href, label in nav_items)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{e(page_title)}</title>
<meta name="description" content="{e(description)}">
<meta name="author" content="{e(name)}">
<meta name="theme-color" content="#f6f5f0">
<meta property="og:type" content="{'article' if article else 'website'}">
<meta property="og:locale" content="zh_CN">
<meta property="og:site_name" content="{e(name)}">
<meta property="og:title" content="{e(page_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(base)}/assets/images/social-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(page_title)}">
<meta name="twitter:description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<link rel="icon" href="{prefix}assets/images/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{e(name)}的博客" href="{prefix}feed.xml">
<script>try{{const t=localStorage.getItem('theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.dataset.theme='dark'}}catch(e){{}}</script>
<link rel="stylesheet" href="{prefix}assets/css/style.css">
<script defer src="{prefix}assets/js/main.js"></script>
</head>
<body>
<a class="skip-link" href="#main">跳到主要内容</a>
<header class="site-header"><div class="container header-inner">
<a class="brand" href="{home}" aria-label="{e(name)}，返回首页"><span class="brand-mark">高<span>俊</span><i></i></span><span class="brand-text">{e(name)}<small>{e(profile['english_name'].upper())}</small></span></a>
<nav class="site-nav" id="site-nav" aria-label="主导航">{nav}</nav>
<div class="header-actions"><button class="icon-button theme-toggle" type="button" aria-label="切换深色模式" title="切换深浅色主题" hidden>{icon('moon', 'moon-icon')}{icon('sun', 'sun-icon')}</button><a class="icon-button github-nav" href="{github}" target="_blank" rel="noopener noreferrer" aria-label="访问 GitHub（新窗口）">{icon('github')}</a><button class="icon-button menu-toggle" type="button" aria-label="展开导航" aria-controls="site-nav" aria-expanded="false" hidden>{icon('menu')}</button></div>
</div></header>
{body}
<footer class="site-footer"><div class="container footer-top"><a class="footer-signature" href="{home}">{e(name)}<span>记录当下，保持好奇。</span></a><div class="footer-links"><a href="{blog}">文章归档</a><a href="{prefix}feed.xml">{icon('rss')} RSS</a><a href="{github}" target="_blank" rel="noopener noreferrer">GitHub {icon('external')}</a></div></div><div class="container footer-bottom"><span>© {date.today().year} {e(name)} · Built with curiosity.</span><span>静态构建 · 托管于 GitHub Pages</span></div></footer>
<button class="back-top icon-button" type="button" aria-label="回到顶部" hidden>{icon('up')}</button>
</body></html>'''


def post_card(post, prefix='', number=None):
    tags = ''.join(f'<span>{e(tag)}</span>' for tag in post['tags'][:2])
    demo = '<span class="demo-label">初始文章</span>' if post.get('demo') else ''
    return f'''<article class="post-card" data-post-slug="{e(post['slug'])}">
<div class="post-meta"><time datetime="{post['date']}">{post['date'].replace('-', '.')}</time><span class="meta-dot">·</span><span>{post['minutes']} 分钟阅读</span>{demo}</div>
<h3><a href="{prefix}blog/{post['slug']}/index.html">{e(post['title'])}</a></h3><p>{e(post['summary'])}</p>
<div class="post-card-bottom"><div class="post-tags">{tags}</div><a class="read-link" href="{prefix}blog/{post['slug']}/index.html" aria-label="阅读：{e(post['title'])}">{icon('arrow')}</a></div></article>'''


def homepage(profile, posts):
    github = 'https://github.com/' + profile['github_username']
    education = ''
    for i, ed in enumerate(profile['education']):
        status = '<span class="status-tag"><i></i> 在读</span>' if ed['current'] else '<span class="completed-tag">已完成</span>'
        education += f'''<article class="education-card"><div class="education-number">0{i+1}</div><div class="education-content"><div class="education-meta"><span>{e(ed['period'])}</span>{status}</div><h3>{e(ed['school'])}<span>{e(ed['degree'])}</span></h3><p>{e(ed['major'])}</p><span class="education-english">SHANDONG UNIVERSITY</span></div>{icon('cap', 'education-icon')}</article>'''
    projects = profile.get('projects', [])
    if projects:
        project_html = '<div class="project-grid">' + ''.join(f'<article class="project-card">{icon("code")}<h3>{e(p["name"])}</h3><p>{e(p["description"])}</p><a class="text-link" href="{e(p["url"])}" target="_blank" rel="noopener noreferrer">查看项目 {icon("external")}</a></article>' for p in projects) + '</div>'
    else:
        project_html = f'''<div class="project-empty"><div class="project-symbol" aria-hidden="true">{icon('code')}</div><div><span class="eyebrow">WORK IN PROGRESS</span><h3>把想法，写成代码。</h3><p>目前暂无公开 GitHub 仓库。后续公开的项目与实践记录，会在这里继续更新。</p></div><a class="button button-outline" href="{github}?tab=repositories" target="_blank" rel="noopener noreferrer">查看 GitHub {icon('external')}</a></div>'''
    cards = ''.join(post_card(post) for post in posts[:2]) or '<p class="empty-state">第一篇记录，即将开始。</p>'
    body = f'''<main id="main">
<section class="hero container" aria-labelledby="hero-title"><div class="hero-copy"><div class="hero-kicker"><span class="tiny-line"></span> HELLO, WORLD <span class="kicker-year">/ 2026</span></div><p class="hero-greeting">你好，很高兴在这里遇见你。</p><h1 id="hero-title">我是<span class="serif-name">{e(profile['name'])}</span><span class="accent-period">。</span></h1><p class="hero-english">{e(profile['english_name'])} <span> / </span> {e(profile['github_username'])}</p><p class="hero-description">{e(profile['tagline'])}<br>一名计算机领域的持续学习者，<br class="desktop-break">在这里记录学习、实践与成长。</p><div class="hero-buttons"><a class="button button-primary" href="blog/index.html">阅读我的博客 {icon('arrow')}</a><a class="button button-quiet" href="{github}" target="_blank" rel="noopener noreferrer">{icon('github')} 访问 GitHub</a></div><div class="hero-location">{icon('cap')} 山东大学<span class="meta-dot">·</span>计算机技术硕士在读</div></div>
<aside class="profile-card" aria-label="个人名片"><div class="profile-card-top"><span>PERSONAL PROFILE</span><span>01 /</span></div><div class="portrait-composition"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><span class="portrait-plus plus-one">+</span><span class="portrait-plus plus-two">+</span><div class="portrait-frame"><img src="assets/images/portrait.png" alt="{e(profile['name'])}的个人照片" width="109" height="148" fetchpriority="high"></div><span class="portrait-label">STAY CURIOUS.</span></div><div class="profile-card-info"><span class="profile-status"><i></i> 持续学习中</span><h2>{e(profile['school'])}</h2><p>{e(profile['status'])}</p></div><div class="profile-card-bottom"><span>{e(profile['hometown'])}</span><span>ZHANG / GAOJUN</span></div></aside>
<div class="hero-bottom"><span>LEARNING · BUILDING · WRITING</span><a href="#about">向下，了解更多 <span>↓</span></a></div></section>
<section class="section about-section" id="about"><div class="container section-grid"><div class="section-heading"><span class="section-label">01 / ABOUT ME</span><h2>保持好奇，<br>步履不停<span class="accent-period">。</span></h2></div><div class="about-content"><p class="lead">{e(profile['intro'])}</p><p>从本科的计算机科学与技术，到硕士阶段的计算机技术，继续学习，也继续探索。希望把零散的知识整理成清晰的脉络，把每一步实践沉淀为可以回看的记录。</p><div class="about-facts"><div><span>当前阶段</span><strong>硕士研究生</strong></div><div><span>所在学校</span><strong>{e(profile['school'])}</strong></div><div><span>我的家乡</span><strong>{e(profile['hometown'])}</strong></div><div><span>线上身份</span><a href="{github}" target="_blank" rel="noopener noreferrer">@{e(profile['github_username'])} {icon('external')}</a></div></div></div></div></section>
<section class="section container" id="education"><div class="section-title-row"><div><span class="section-label">02 / EDUCATION</span><h2>求学之路</h2></div><p class="section-note">每一段经历，都是新的起点。</p></div><div class="education-timeline">{education}</div></section>
<section class="section practice-section" id="projects"><div class="container"><div class="section-title-row"><div><span class="section-label">03 / EXPLORATION</span><h2>项目与实践</h2></div><span class="section-note">从想法到实现，一步一步来。</span></div>{project_html}</div></section>
<section class="section container writing-section" id="writing"><div class="section-title-row"><div><span class="section-label">04 / WRITING</span><h2>一些记录，慢慢积累。</h2></div><a class="text-link" href="blog/index.html">全部文章 {icon('arrow')}</a></div><div class="post-grid">{cards}</div></section>
<section class="container contact-section"><div><span class="section-label">LET'S CONNECT</span><h2>以代码相识，<span class="serif-name">以交流同行。</span></h2><p>欢迎来 GitHub 看看，也欢迎围绕学习与技术交流想法。</p></div><a class="contact-link" href="{github}" target="_blank" rel="noopener noreferrer">{icon('github')}<span>@{e(profile['github_username'])}</span>{icon('external')}</a></section>
</main>'''
    return layout(profile, '', body)


def blogpage(profile, posts):
    tags = sorted({tag for p in posts for tag in p['tags']})
    filters = '<button type="button" class="filter-chip active" data-filter="" aria-pressed="true">全部文章 <span>' + str(len(posts)) + '</span></button>'
    filters += ''.join(f'<button type="button" class="filter-chip" data-filter="{e(tag)}" aria-pressed="false">{e(tag)}</button>' for tag in tags)
    data = [dict(slug=p['slug'], title=p['title'], summary=p['summary'], tags=p['tags'], text=p['source']) for p in posts]
    search_json = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    body = f'''<main id="main" class="container blog-main"><div class="page-heading"><span class="section-label">THE JOURNAL / 文章与学习记录</span><h1>写下所学，<br>也写下<span class="serif-name">所想。</span></h1><p>把思考留给文字，让每一次积累都有迹可循。</p><a class="rss-link" href="../feed.xml">{icon('rss')} RSS 订阅</a></div><section class="blog-library" aria-labelledby="library-title"><h2 id="library-title" class="visually-hidden">文章列表</h2><div class="blog-toolbar"><div class="filter-list" role="group" aria-label="按标签筛选" hidden>{filters}</div><label class="search-box" hidden>{icon('search')}<span class="visually-hidden">搜索文章</span><input id="post-search" type="search" placeholder="搜索文章、标签或关键词…" autocomplete="off"><kbd>/</kbd></label></div><div class="blog-count"><span id="result-count" role="status" aria-live="polite">共 {len(posts)} 篇文章</span><span>持续记录，慢慢更新</span></div><div class="post-grid blog-posts">{''.join(post_card(p, '../') for p in posts)}</div><div class="search-empty" hidden><span aria-hidden="true">{icon('search')}</span><h3>暂时没有找到相关记录</h3><p>换个关键词试试，或清除当前筛选。</p><button type="button" class="button button-outline" id="reset-search">清除筛选</button></div></section><script type="application/json" id="post-data">{search_json}</script></main>'''
    return layout(profile, '博客', body, prefix='../', active='blog', path='blog/', description='张高俊的文章与学习记录，记录计算机技术、代码实践与日常思考。')


def articlepage(profile, post, posts):
    tags = ''.join(f'<a href="../index.html?tag={quote(tag)}">{e(tag)}</a>' for tag in post['tags'])
    toc = ''.join(f'<li class="toc-level-{level}"><a href="#{anchor}">{e(title)}</a></li>' for anchor, title, level in post['toc'])
    notice = '<div class="demo-notice"><span>初始示例</span>这篇文章随站点一同提供，便于演示与上手。发布前可按你的真实想法修改，或直接删除。</div>' if post.get('demo') else ''
    others = [p for p in posts if p['slug'] != post['slug']][:2]
    related = ''.join(f'<a href="../{p["slug"]}/index.html"><span>继续阅读</span><strong>{e(p["title"])}</strong>{icon("arrow")}</a>' for p in others)
    body = f'''<main id="main" class="container article-main"><a class="back-link" href="../index.html">← 返回文章列表</a><header class="article-heading"><div class="post-tags">{tags}</div><h1>{e(post['title'])}</h1><p class="article-summary">{e(post['summary'])}</p><div class="article-byline"><img src="../../assets/images/portrait.png" width="36" height="36" alt=""><span>{e(profile['name'])}</span><span class="meta-dot">·</span><time datetime="{post['date']}">{post['date'].replace('-', '.')}</time><span class="meta-dot">·</span><span>{post['minutes']} 分钟阅读</span></div></header><div class="article-grid"><article class="article-body">{notice}{post['body']}<div class="article-end"><span>· · ·</span><p>感谢阅读，愿每次记录都有收获。</p></div><div class="article-navigation">{related}</div></article><aside class="article-toc"><div class="toc-sticky"><span class="section-label">ON THIS PAGE</span><h2>文章目录</h2><nav aria-label="文章目录"><ol>{toc}</ol></nav><a class="toc-back" href="../index.html">查看全部文章 {icon('arrow')}</a></div></aside></div></main>'''
    return layout(profile, post['title'], body, prefix='../../', active='blog', path=f'blog/{post["slug"]}/', description=post['summary'], article=True)


def notfound(profile):
    # Absolute URLs make this work at arbitrary nested nonexistent paths on Pages.
    base = profile['site_url'].rstrip('/') + '/'
    body = f'''<main id="main" class="container not-found"><span class="section-label">LOST IN THE GARDEN</span><p class="error-number">404<span>.</span></p><h1>这条小路，还没有通向文章。</h1><p>页面可能已移动，或者地址有一点小小的偏差。</p><div><a class="button button-primary" href="{e(base)}">返回首页 {icon('arrow')}</a><a class="button button-outline" href="{e(base)}blog/">看看博客</a></div></main>'''
    page = layout(profile, '页面未找到', body, prefix=base, active='', path='404.html')
    return page.replace('<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="canonical"')


def write_output(files):
    OUT.mkdir(exist_ok=True)
    manifest = OUT / '.build-manifest.json'
    old_files = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    for relative, content in files.items():
        target = (OUT / relative).resolve()
        if not target.is_relative_to(OUT.resolve()):
            raise ValueError('Output path escaped _site')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    assets = []
    for source in (ROOT / 'assets').rglob('*'):
        if source.is_file():
            relative = source.relative_to(ROOT).as_posix()
            target = OUT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            assets.append(relative)
    current = set(files) | set(assets)
    for relative in set(old_files) - current:
        target = (OUT / relative).resolve()
        if not target.is_relative_to(OUT.resolve()) or target == OUT.resolve():
            raise ValueError('Unsafe stale output path')
        if target.is_file():
            print(f'Removing stale generated output: {target}')
            target.unlink()
    manifest.write_text(json.dumps(sorted(current), ensure_ascii=False, indent=2), encoding='utf-8')


def build():
    profile, posts = load_content()
    base = profile['site_url'].rstrip('/')
    files = {'index.html': homepage(profile, posts), 'blog/index.html': blogpage(profile, posts),
             '404.html': notfound(profile), '.nojekyll': ''}
    for post in posts:
        files[f'blog/{post["slug"]}/index.html'] = articlepage(profile, post, posts)
    urls = [base + '/', base + '/blog/'] + [f'{base}/blog/{p["slug"]}/' for p in posts]
    files['sitemap.xml'] = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{e(url)}</loc></url>' for url in urls) + '</urlset>'
    files['robots.txt'] = f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n'
    items = ''
    for post in posts:
        url = f'{base}/blog/{post["slug"]}/'
        day = date.fromisoformat(post['date'])
        # Feed time is explicitly in the author's Asia/Shanghai time zone.
        published = day.strftime('%a, %d %b %Y') + ' 00:00:00 +0800'
        items += f'<item><title>{e(post["title"])}</title><link>{e(url)}</link><guid isPermaLink="true">{e(url)}</guid><description>{e(post["summary"])}</description><pubDate>{published}</pubDate></item>'
    files['feed.xml'] = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>{e(profile["name"])}的博客</title><link>{base}/blog/</link><description>{e(profile["description"])}</description><language>zh-CN</language><atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>{items}</channel></rss>'
    write_output(files)
    print(f'Built {len(posts)} posts -> {OUT}')
    check()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.duplicate_ids = [], set(), []
        self.h1 = 0
        self.title = False
        self.lang = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html': self.lang = attrs.get('lang')
        if tag == 'h1': self.h1 += 1
        if tag == 'title': self.title = True
        if 'id' in attrs:
            if attrs['id'] in self.ids: self.duplicate_ids.append(attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'img' and 'alt' not in attrs:
            raise ValueError('Image missing alt attribute')
        for key in ('href', 'src'):
            if key in attrs: self.refs.append(attrs[key])


def check():
    errors, pages = [], {}
    for path in OUT.rglob('*.html'):
        page = PageParser()
        page.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = page
        if page.h1 != 1 or not page.title or page.lang != 'zh-CN' or page.duplicate_ids:
            errors.append(f'{path.relative_to(OUT)}: invalid page metadata, h1, or duplicate IDs')
    if not pages:
        raise ValueError('No built pages. Run python site.py build first.')
    for path, page in pages.items():
        for ref in page.refs:
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc:
                continue
            target = (OUT / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/') else path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if target.is_dir(): target = target / 'index.html'
            if not target.is_relative_to(OUT.resolve()) or not target.is_file():
                errors.append(f'{path.relative_to(OUT)}: broken local link {ref}')
            elif parsed.fragment and target in pages and unquote(parsed.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(OUT)}: missing anchor {ref}')
    for name in ('sitemap.xml', 'feed.xml'):
        ET.parse(OUT / name)
    if not (OUT / 'assets/images/social-card.png').is_file():
        errors.append('Missing social preview image')
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'PASS: {len(pages)} HTML pages, local links, anchors, image alt text, RSS and sitemap.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check', 'serve'])
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if args.command == 'build': build()
    elif args.command == 'check': check()
    else:
        if not (OUT / 'index.html').exists(): build()
        from functools import partial
        handler = partial(SimpleHTTPRequestHandler, directory=str(OUT))
        print(f'Preview: http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.server_close()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
