#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'GEARUP-PD-BLOG'
BLOG_DIR = CONTENT / 'Blog'
DIST = ROOT / 'dist'
BLOG_OUT = DIST / 'blog'
ASSETS = DIST / 'assets'
IMAGES_OUT = DIST / 'images'
RESOURCES_MD = CONTENT / 'Resources.md'
LANDING_MD = CONTENT / 'GEARUP-PD.md'
SIGN_UP_MD = CONTENT / 'Sign Up.md'
ABOUT_MD = CONTENT / 'About.md'
LOGO_PNG = CONTENT / 'Images' / 'gearup_logo.png'
NEURA_LOGO = CONTENT / 'Images' / 'neura_logo.webp'

SITE_TITLE = 'GEARUP-PD'
SITE_SUBTITLE = "Genetic-Environmental associations in Australian Rural and Underrepresented Populations with Parkinson's Disease study"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or 'page'


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def format_date(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime('%d %b %Y')


def note_href(name: str) -> str:
    slug = slugify(name)
    if slug == 'gearup-pd':
        return 'index.html'
    if slug == 'resources':
        return 'resources.html'
    if slug == 'sign-up':
        return 'sign-up.html'
    if slug == 'about':
        return 'about.html'
    return f'{slug}.html'


def image_href(name: str) -> str:
    return f'images/{name}'


def markdown_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(
        r'!\[\[([^\]]+)\]\]',
        lambda m: f'<img class="inline-image" src="{image_href(m.group(1))}" alt="{html.escape(Path(m.group(1)).stem)}">',
        text,
    )
    text = re.sub(r'&lt;br\s*/?&gt;', '<br>', text, flags=re.IGNORECASE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', lambda m: f'<a href="{note_href(m.group(1))}">{m.group(2)}</a>', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', lambda m: f'<a href="{note_href(m.group(1))}">{m.group(1)}</a>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    bare_url = re.compile(r'(?<!["\'>])(https?://[^\s<]+)')
    text = bare_url.sub(r'<a href="\1">\1</a>', text)
    text = re.sub(r'(?<![\w.])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'<a href="mailto:\1">\1</a>', text)
    return text


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip('|')
    return [cell.strip() for cell in stripped.split('|')]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells)


def render_table(table_lines: list[str]) -> str:
    headers = split_table_row(table_lines[0])
    body_lines = table_lines[2:] if len(table_lines) > 1 and is_table_separator(table_lines[1]) else table_lines[1:]
    thead = ''.join(f'<th>{markdown_inline(cell)}</th>' for cell in headers)
    rows = []
    for line in body_lines:
        cells = split_table_row(line)
        if not any(cells):
            continue
        row = ''.join(f'<td>{markdown_inline(cell)}</td>' for cell in cells)
        rows.append(f'<tr>{row}</tr>')
    tbody = ''.join(rows)
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>'


def markdown_to_html(md: str) -> str:
    lines = md.replace('\r\n', '\n').split('\n')
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{markdown_inline(' '.join(x.strip() for x in paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = ''.join(f'<li>{markdown_inline(item)}</li>' for item in list_items)
            blocks.append(f'<ul>{items}</ul>')
            list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            blocks.append(render_table(table_lines))
            table_lines = []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if '|' in stripped and stripped.count('|') >= 2:
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        flush_table()
        if line.startswith('#'):
            flush_paragraph()
            flush_list()
            level = len(line) - len(line.lstrip('#'))
            content = line[level:].strip()
            anchor = slugify(content)
            blocks.append(f'<h{level} id="{anchor}">{markdown_inline(content)}</h{level}>')
            continue
        if re.match(r'^[-*]\s+', line):
            flush_paragraph()
            list_items.append(re.sub(r'^[-*]\s+', '', line).strip())
            continue
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_table()
    return '\n'.join(blocks)


def collect_posts() -> list[dict]:
    posts = []
    for path in sorted(BLOG_DIR.glob('*.md')):
        stat = path.stat()
        created = getattr(stat, 'st_birthtime', stat.st_mtime)
        text = read_text(path).strip()
        title = None
        for line in text.splitlines():
            if line.strip().startswith('#'):
                title = re.sub(r'^#+\s*', '', line.strip())
                break
        if not title:
            title = path.stem
        excerpt = ''
        for line in text.splitlines():
            clean = line.strip()
            if clean and not clean.startswith('#'):
                excerpt = clean
                break
        slug = slugify(path.stem)
        posts.append({
            'path': path,
            'slug': slug,
            'title': title,
            'created': created,
            'created_label': format_date(created),
            'excerpt': excerpt,
            'content': text,
        })
    posts.sort(key=lambda p: p['created'], reverse=True)
    return posts


def sidebar_html(posts: list[dict], current: str | None = None, depth: int = 0) -> str:
    prefix = '../' if depth else './'
    page_items = [
        f'<li><a class="{"active" if current == "index" else ""}" href="{prefix}index.html">Home</a></li>',
        f'<li><a class="{"active" if current == "resources" else ""}" href="{prefix}resources.html">Resources</a></li>',
        f'<li><a class="{"active" if current == "sign-up" else ""}" href="{prefix}sign-up.html">Sign Up</a></li>',
        f'<li><a class="{"active" if current == "about" else ""}" href="{prefix}about.html">About</a></li>',
    ]
    blog_items = []
    for post in posts:
        href = f'./{post["slug"]}.html' if depth else f'./blog/{post["slug"]}.html'
        active = 'active' if current == post['slug'] else ''
        blog_items.append(
            f'<li><a class="{active}" href="{href}"><span>{html.escape(post["title"])}</span><small>{post["created_label"]}</small></a></li>'
        )
    blog_html = ''.join(blog_items) or '<li><span class="empty-state">No blog posts yet.</span></li>'
    return f'''
      <section class="sidebar-section sidebar-pages">
        <h2>Main Navigation</h2>
        <ul class="nav-list nav-primary">{''.join(page_items)}</ul>
      </section>
      <section class="sidebar-section sidebar-blog">
        <h2>Project Updates</h2>
        <ul class="nav-list nav-blog">{blog_html}</ul>
      </section>
    '''


def page_shell(title: str, body: str, posts: list[dict], current: str | None = None, depth: int = 0) -> str:
    prefix = '../' if depth else './'
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · {SITE_TITLE}</title>
  <link rel="icon" type="image/png" href="{prefix}images/gearup_logo.png">
  <link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-header">
        <a class="sidebar-logo" href="{prefix}index.html" aria-label="{SITE_TITLE} home">
          <img src="{prefix}images/gearup_logo.png" alt="{SITE_TITLE}">
        </a>
      </div>
      <nav>
        {sidebar_html(posts, current, depth)}
      </nav>
      <div class="sidebar-spacer"></div>
      <div class="sidebar-footer">
        <img src="{prefix}images/neura_logo.webp" alt="NeuRA">
      </div>
    </aside>
    <main class="content">
      {body}
    </main>
  </div>
</body>
</html>
'''


def build_landing(posts: list[dict]) -> str:
    source_md = read_text(LANDING_MD)
    intro_html = markdown_to_html(source_md)
    updates = ''.join(
        f'<li><a href="./blog/{p["slug"]}.html"><span>{html.escape(p["title"])}</span><time datetime="{dt.datetime.fromtimestamp(p["created"]).date().isoformat()}">{p["created_label"]}</time></a></li>'
        for p in posts[:5]
    ) or '<li><span>No blog posts yet.</span></li>'
    body = f'''
    <section class="hero banner-hero">
      <div>
        <h1>{SITE_TITLE}</h1>
        <p class="study-subtitle">{SITE_SUBTITLE}</p>
      </div>
    </section>
    <section class="content-card updates-module">
      <div class="section-heading">
        <h2>Project Updates</h2>
        <p>The five most recent blog posts.</p>
      </div>
      <ol class="recent-list">{updates}</ol>
    </section>
    <section class="content-card markdown-module">
      {intro_html}
    </section>
    '''
    return page_shell(SITE_TITLE, body, posts, current='index', depth=0)


def build_post(post: dict, posts: list[dict]) -> str:
    body = f'''
    <article class="content-card blog-post">
      <p class="eyebrow">Blog update · {post['created_label']}</p>
      {markdown_to_html(post['content'])}
      <p class="muted">File source: {html.escape(post['path'].name)}</p>
    </article>
    '''
    return page_shell(post['title'], body, posts, current=post['slug'], depth=1)


def build_simple_page(title: str, markdown_path: Path, fallback_html: str, posts: list[dict], current: str) -> str:
    if markdown_path.exists() and markdown_path.read_text(encoding='utf-8').strip():
        content_html = markdown_to_html(read_text(markdown_path))
    else:
        content_html = fallback_html
    body = f'<section class="content-card">{content_html}</section>'
    return page_shell(title, body, posts, current=current, depth=0)


def build_resources(posts: list[dict]) -> str:
    return build_simple_page(
        'Resources',
        RESOURCES_MD,
        '<h1>Resources</h1><p>Resource links and participant materials can be added here later.</p>',
        posts,
        current='resources',
    )


def build_sign_up(posts: list[dict]) -> str:
    return build_simple_page(
        'Sign Up',
        SIGN_UP_MD,
        '<h1>Sign Up</h1><p>Sign-up information can be added here later.</p>',
        posts,
        current='sign-up',
    )


def build_about(posts: list[dict]) -> str:
    return build_simple_page(
        'About',
        ABOUT_MD,
        '<h1>About</h1><p>About information can be added here later.</p>',
        posts,
        current='about',
    )


def build_blog_index(posts: list[dict]) -> str:
    cards = ''.join(
        f'<article class="post-card">'
        f'<p class="post-date">{p["created_label"]}</p>'
        f'<h2><a href="./{p["slug"]}.html">{html.escape(p["title"])} </a></h2>'
        f'<p>{html.escape(p["excerpt"] or "Open the update to read more.")}</p>'
        f'</article>'
        for p in posts
    ) or '<p>No blog posts yet.</p>'
    body = f'''
    <section class="hero hero-compact">
      <div>
        <p class="eyebrow">Project updates</p>
        <h1>Blog</h1>
        <p class="lead">News, announcements, and progress updates for the GEARUP-PD study.</p>
      </div>
    </section>
    <section class="content-card">
      <h2>All updates</h2>
      <div class="post-grid">{cards}</div>
    </section>
    '''
    return page_shell('Blog', body, posts, current='blog-index', depth=1)


def copy_static_assets() -> None:
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    images_src = CONTENT / 'Images'
    if images_src.exists():
        for path in images_src.iterdir():
            if path.is_file():
                shutil.copy2(path, IMAGES_OUT / path.name)
    if LOGO_PNG.exists():
        shutil.copy2(LOGO_PNG, IMAGES_OUT / 'gearup_logo.png')
    if NEURA_LOGO.exists():
        shutil.copy2(NEURA_LOGO, IMAGES_OUT / 'neura_logo.webp')


def write_styles() -> None:
    styles = '''
:root {
  --bg: #eff4fb;
  --card: #ffffff;
  --ink: #102038;
  --muted: #5d6b82;
  --line: #dbe3f0;
  --accent: #2667ff;
  --accent-soft: #eaf1ff;
  --shadow: 0 18px 40px rgba(16,32,56,0.08);
  --blog-bg: #0f1c33;
  --blog-card: #132543;
  --blog-line: rgba(255,255,255,0.1);
  --blog-ink: #edf4ff;
  --blog-muted: #b9c7de;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: linear-gradient(180deg, #f7f9fc 0%, #eef3fb 100%);
  color: var(--ink);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.app-shell { display: grid; grid-template-columns: 320px minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  padding: 28px 22px; border-right: 1px solid var(--line); background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
  display: flex; flex-direction: column;
}
.sidebar-header { margin-bottom: 22px; display: flex; justify-content: center; }
.sidebar-logo {
  display: inline-flex; align-items: center; justify-content: center;
  text-decoration: none; width: 100%;
}
.sidebar-logo img {
  display: block; max-width: 154px; width: 100%; height: auto;
}
.sidebar-section { margin-bottom: 18px; }
.sidebar-section h2 {
  margin: 0 0 10px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.12em; color: #567;
}
.sidebar-spacer { flex: 1; }
.sidebar-footer {
  margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--line);
  display: flex; justify-content: center; align-items: center;
}
.sidebar-footer img {
  display: block; max-width: 180px; width: 100%; height: auto;
}
.sidebar-blog {
  margin-top: 22px; padding: 16px; border-radius: 22px; background: linear-gradient(180deg, var(--blog-bg), #162b4f);
  box-shadow: var(--shadow);
}
.sidebar-blog h2 { color: var(--blog-ink); }
.eyebrow { text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.75rem; color: #567; font-weight: 700; }
.nav-list { list-style: none; margin: 0; padding: 0; }
.nav-list li { margin-bottom: 8px; }
.nav-list a {
  display: flex; flex-direction: column; gap: 4px;
  padding: 12px 14px; border-radius: 14px; color: var(--ink); background: transparent; border: 1px solid transparent;
}
.nav-primary a:hover, .nav-primary a.active { background: var(--accent-soft); border-color: #cfe0ff; text-decoration: none; }
.nav-blog a {
  color: var(--blog-ink); background: rgba(255,255,255,0.03); border-color: transparent;
}
.nav-blog a:hover, .nav-blog a.active { background: rgba(255,255,255,0.09); border-color: var(--blog-line); text-decoration: none; }
.nav-list small, .empty-state { color: var(--muted); }
.nav-blog small, .nav-blog .empty-state { color: var(--blog-muted); }
.content { padding: 36px; }
.hero {
  background: radial-gradient(circle at top left, #d9e8ff, #ffffff 55%);
  border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 28px; padding: 40px; margin-bottom: 24px;
}
.banner-hero {
  min-height: 260px; display: flex; align-items: end;
  background: linear-gradient(135deg, #0f4d3a 0%, #16634b 50%, #2a7a5f 100%);
  color: white;
}
.banner-hero .eyebrow, .banner-hero .study-subtitle { color: rgba(255,255,255,0.92); }
.hero h1 { margin: 8px 0 14px; font-size: clamp(2.7rem, 6vw, 4.8rem); line-height: 0.98; }
.study-subtitle { font-size: 1.25rem; line-height: 1.6; max-width: 60rem; margin: 0; }
.lead { font-size: 1.1rem; line-height: 1.7; color: #28405f; max-width: 60rem; }
.content-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 24px; padding: 28px; box-shadow: var(--shadow); margin-bottom: 24px;
}
.section-heading { margin-bottom: 12px; }
.section-heading h2 { margin: 0 0 6px; }
.section-heading p { margin: 0; color: var(--muted); }
.post-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 18px; }
.post-card { border: 1px solid var(--line); border-radius: 18px; padding: 18px; background: #fbfdff; }
.post-card h2, .post-card h3 { margin: 4px 0 8px; }
.post-date, .muted { color: var(--muted); }
.blog-post h1, .blog-post h2, .content-card h1, .content-card h2, .content-card h3 { line-height: 1.2; }
.recent-list { margin: 0; padding: 0; list-style: none; }
.recent-list li { margin: 12px 0; }
.recent-list a {
  display: flex; justify-content: space-between; gap: 12px; align-items: center;
  padding: 16px 18px; border-radius: 16px; border: 1px solid var(--line);
  background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%);
  box-shadow: 0 10px 24px rgba(16,32,56,0.06);
  color: var(--ink); font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}
.recent-list a:hover {
  text-decoration: none; transform: translateY(-1px);
  border-color: #bfd3ff; background: linear-gradient(180deg, #ffffff 0%, #edf4ff 100%);
  box-shadow: 0 14px 28px rgba(16,32,56,0.1);
}
.recent-list a span { display: block; }
.recent-list time {
  color: var(--muted); white-space: nowrap; font-size: 0.95rem; font-weight: 500;
  background: #eef4ff; padding: 6px 10px; border-radius: 999px;
}
.markdown-module h1 { margin-top: 0; }
.markdown-module h2 { scroll-margin-top: 24px; }
.inline-image {
  max-width: 200px; width: 100%; height: auto; display: block;
  border-radius: 18px; object-fit: cover;
}
.table-wrap {
  width: 100%; overflow-x: auto; margin: 1rem 0;
}
.table-wrap table {
  width: 100%; border-collapse: collapse; min-width: 760px;
}
.table-wrap th, .table-wrap td {
  border: 1px solid var(--line); padding: 14px; text-align: left; vertical-align: top;
}
.table-wrap th {
  background: #eef4ff; font-weight: 700;
}
.table-wrap tr:nth-child(even) td {
  background: #fbfdff;
}
.table-wrap p:first-child { margin-top: 0; }
.table-wrap p:last-child { margin-bottom: 0; }
code { background: #eff4fb; padding: 2px 7px; border-radius: 8px; }
@media (max-width: 980px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { position: relative; height: auto; }
  .content { padding: 18px; }
  .hero { padding: 28px; }
  .recent-list a { flex-direction: column; align-items: flex-start; }
}
'''
    (ASSETS / 'styles.css').write_text(styles, encoding='utf-8')


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    BLOG_OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)

    posts = collect_posts()
    (DIST / 'index.html').write_text(build_landing(posts), encoding='utf-8')
    (DIST / 'resources.html').write_text(build_resources(posts), encoding='utf-8')
    (DIST / 'sign-up.html').write_text(build_sign_up(posts), encoding='utf-8')
    (DIST / 'about.html').write_text(build_about(posts), encoding='utf-8')
    (BLOG_OUT / 'index.html').write_text(build_blog_index(posts), encoding='utf-8')
    for post in posts:
        (BLOG_OUT / f"{post['slug']}.html").write_text(build_post(post, posts), encoding='utf-8')
    copy_static_assets()
    write_styles()


if __name__ == '__main__':
    build()
    print(f'Built site in {DIST}')
