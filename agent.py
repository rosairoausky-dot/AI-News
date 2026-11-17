"""Public-source research runner; Python standard library only."""
import argparse
import concurrent.futures
import hashlib
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
DOMAINS = {'video': 'AI 视频', 'music': 'AI 音乐', 'world': '世界模型'}
TERMS = {'video': ['video', '视频', 'sora', 'veo', 'kling', 'seedance', '可灵', '海螺', 'vidu'], 'music': ['music', '音乐', 'suno', 'udio', 'lyria', 'audiocraft'], 'world': ['world model', '世界模型', 'spatial intelligence', 'cosmos', 'genie', 'v-jepa', '空间智能', 'world labs']}
CATEGORIES = {'融资与并购': ['funding', 'raised', 'acquisition', '融资', '收购', '并购'], '政策与版权': ['copyright', 'lawsuit', 'regulation', '版权', '监管', '诉讼'], '人才与组织': ['joins', 'appointed', 'hiring', '离职', '加入', '招聘', '任命'], '合作与市场': ['partnership', 'partners', 'market', '合作', '市场'], '产品与商业化': ['launch', 'release', 'pricing', '发布', '上线', '价格'], '技术与论文': ['paper', 'research', 'benchmark', '论文', '研究', '评测']}


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', str(s or '')))).strip()


def timestamp(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        try:
            d = parsedate_to_datetime(s)
        except (ValueError, TypeError):
            return None
    # Do not guess an unknown source timezone.
    return d if d.tzinfo else None


def safe_url(s):
    try:
        u = urlsplit(s)
        return u.scheme in ('https', 'http') and bool(u.hostname) and not u.username
    except ValueError:
        return False


def canonical(url):
    u = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.startswith('utm_')]
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, urlencode(query), ''))


def parse_feed(raw):
    root = ET.fromstring(raw)
    items = []
    for entry in root.iter():
        if entry.tag.split('}')[-1] not in ('item', 'entry'):
            continue
        fields, link = {}, ''
        for node in entry:
            key = node.tag.split('}')[-1]
            fields[key] = ''.join(node.itertext())
            if key == 'link' and node.get('rel', 'alternate') == 'alternate':
                link = node.get('href') or node.text or ''
        if fields.get('title') and safe_url(link.strip()):
            items.append({'title': clean(fields['title']), 'url': link.strip(), 'summary': clean(fields.get('description') or fields.get('summary') or fields.get('encoded'))[:1000], 'publishedAt': fields.get('pubDate') or fields.get('published') or fields.get('updated')})
    return items


def fetch_source(source):
    error = ''
    for attempt in range(2):
        try:
            headers = {'User-Agent': 'AI-Frontier-Research-Agent/1.0', 'Accept': 'application/json,application/rss+xml,application/atom+xml,*/*'}
            if urlsplit(source['url']).hostname == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
                headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
            with urlopen(Request(source['url'], headers=headers), timeout=18) as r:
                raw = r.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('响应超过 8 MB')
            kind = source.get('kind', 'rss')
            if kind == 'rss':
                rows = parse_feed(raw)
            elif kind == 'github':
                rows = [{'title': x['commit']['message'].split('\n')[0], 'summary': x['commit']['message'][:1000], 'url': x['html_url'], 'publishedAt': x['commit']['committer']['date']} for x in json.loads(raw)]
            elif kind == 'hf':
                rows = [{'title': x['id'] + ' · 模型卡/仓库更新', 'summary': ', '.join(x.get('tags', [])[:15]), 'url': 'https://huggingface.co/' + x['id'], 'publishedAt': x.get('lastModified')} for x in json.loads(raw)]
            else:
                raise ValueError('不支持的来源类型')
            return source, rows, None
        except Exception as exc:
            error = str(exc)[:200]
            if attempt == 0:
                time.sleep(1)
    return source, [], error


def classify(row, source):
    corpus = (row['title'] + ' ' + row.get('summary', '')).lower()
    domains = set(source.get('domains', []))
    domains.update(d for d, words in TERMS.items() if any(w in corpus for w in words))
    if not domains:
        return None
    category = '开源与生态' if source.get('kind') in ('github', 'hf') else next((c for c, words in CATEGORIES.items() if any(w in corpus for w in words)), '行业观察')
    row = dict(row)
    row.update(domains=sorted(domains), category=category, source=source['name'], sourceUrl=source['url'], evidence=source.get('evidence', 'discovery'), verification='来源摘录，待原文核验', id=hashlib.sha256(canonical(row['url']).encode()).hexdigest()[:24])
    return row


def assemble(results, end):
    start = end - timedelta(days=7)
    items, undated, statuses, seen = [], [], [], set()
    for source, rows, error in results:
        accepted, missing = 0, 0
        for row in rows:
            if not safe_url(row.get('url', '')):
                continue
            item = classify(row, source)
            if not item:
                continue
            dt = timestamp(item.get('publishedAt'))
            if dt and not start < dt <= end:
                continue
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            item['retrievedAt'] = end.isoformat()
            item['publishedAt'] = dt.isoformat() if dt else None
            if dt:
                items.append(item)
                accepted += 1
            else:
                undated.append(item)
                missing += 1
        statuses.append({'name': source['name'], 'url': source['url'], 'ok': error is None, 'error': error, 'retrieved': len(rows), 'weekly': accepted, 'undated': missing})
    items.sort(key=lambda x: timestamp(x['publishedAt']), reverse=True)
    return {'title': '行业动态', 'generatedAt': end.isoformat(), 'windowStart': start.isoformat(), 'windowEnd': end.isoformat(), 'timezone': 'Asia/Shanghai', 'status': 'partial' if any(not s['ok'] for s in statuses) else 'complete', 'items': items, 'undated': undated, 'sources': statuses, 'gaps': ['X / 小红书 / 微信公众号未接入云端账号采集；搜索收录不等于平台完整覆盖。', '关键词归类为启发式结果；融资、人员、版权等事实需原文核验。', 'RSS/API 返回数量有限，不保证七天内全部事件均被收录。']}


def md(s):
    return str(s).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ')


def markdown(report):
    lines = ['# 行业动态 · ' + report['windowEnd'][:10], '', f"检索窗口：{report['windowStart']} 至 {report['windowEnd']}（北京时间）。", '', f"本周条目：{len(report['items'])}；无发布日期待核验：{len(report['undated'])}；采集状态：{'部分来源失败，报告不完整' if report['status']=='partial' else '配置来源完成检索（不代表全网覆盖）'}。", '', '内容为来源摘录与自动分类，未经逐条原文事实核验。', '']
    for category in list(CATEGORIES) + ['开源与生态', '行业观察']:
        rows = [r for r in report['items'] if r['category'] == category]
        lines += ['## ' + category, '']
        if not rows:
            lines += ['本期未检索到符合窗口的条目；不代表行业没有事件。', '']
        for row in rows:
            lines += [f"### [{md(row['title'])}]({row['url'].replace(' ', '%20').replace(')', '%29')})", '', ' / '.join(DOMAINS[d] for d in row['domains']) + f" · {md(row['source'])} · {row['publishedAt']}", '', md(row.get('summary') or '来源未提供摘要，请查看原文。'), '', f"证据：{row['evidence']}；{row['verification']}。", '']
    lines += ['## 无发布日期，待核验', '']
    lines += [f"- [{md(x['title'])}]({x['url']}) · {md(x['source'])}" for x in report['undated']] or ['无。']
    lines += ['', '## 来源状态', '']
    for s in report['sources']:
        lines.append(f"- {md(s['name'])}：{'成功' if s['ok'] else '失败'}；原始 {s['retrieved']}，本周去重后 {s['weekly']}。{md(s['error'] or '')}")
    lines += ['', '## 覆盖缺口', ''] + ['- ' + x for x in report['gaps']]
    return '\n'.join(lines) + '\n'


def webpage(report, history):
    payload = json.dumps(report, ensure_ascii=False).replace('<', '\\u003c')
    links = ''.join(f'<a href="../reports/{x}.md">{x}</a> ' for x in history)
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>行业动态 · AI Frontier Agent</title>
<style>body{background:#101820;color:#e3ecef;font:15px/1.7 system-ui;margin:0}main{max-width:1120px;margin:auto;padding:38px 24px}h1{font-size:38px;margin:0}a{color:#70d8cf}header p,.muted{color:#9eb4bf}nav,section,article{margin:20px 0}nav{display:flex;gap:12px;flex-wrap:wrap}input,select{background:#192b36;color:#e3ecef;padding:12px;border:1px solid #47606b;border-radius:8px}input{flex:1;min-width:180px}article{background:#192731;border:1px solid #354c57;padding:22px;border-radius:14px}h2{font-size:19px;margin:0 0 8px}.tag{display:inline-block;color:#75ded0;font-size:12px;margin-right:12px}summary{cursor:pointer}li{margin:8px 0}.status{color:#efc67a}#history a{margin-right:12px}</style>
<main><header><div class="tag">AI FRONTIER / WEEKLY INTELLIGENCE</div><h1>行业动态</h1><p>AI 视频 · AI 音乐 · 世界模型｜每周四北京时间 09:00 自动检索发布</p><p id="window"></p><p class="status" id="status"></p></header><nav><input id="query" placeholder="搜索公司、项目、事件"><select id="domain"><option value="">全部领域</option><option value="video">AI 视频</option><option value="music">AI 音乐</option><option value="world">世界模型</option></select><select id="category"><option value="">全部事件</option></select></nav><div id="count"></div><section id="news"></section><details><summary>采集状态、待核验与覆盖缺口</summary><div id="sources"></div></details><section id="history"><h2>历史周报</h2>''' + links + '''</section></main><script type="application/json" id="data">''' + payload + '''</script><script>
const d=JSON.parse(document.getElementById('data').textContent),e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
document.getElementById('window').textContent=d.windowStart+' 至 '+d.windowEnd;
document.getElementById('status').textContent=(d.status==='partial'?'部分来源失败，报告不完整。':'配置来源检索完成。')+' 内容为来源摘录，待原文核验。';
const q=document.getElementById('query'),dom=document.getElementById('domain'),cat=document.getElementById('category');for(const c of [...new Set(d.items.map(x=>x.category))]){const o=document.createElement('option');o.textContent=c;cat.append(o)}
function render(){const rows=d.items.filter(x=>(!dom.value||x.domains.includes(dom.value))&&(!cat.value||x.category===cat.value)&&JSON.stringify(x).toLowerCase().includes(q.value.toLowerCase()));document.getElementById('count').textContent=rows.length+' 条动态';document.getElementById('news').innerHTML=rows.map(x=>`<article><div class="tag">${e(x.category)}</div><div class="tag">${e(x.source)}</div><h2><a href="${e(x.url)}" target="_blank" rel="noreferrer">${e(x.title)}</a></h2><div class="muted">${e(x.publishedAt)} · ${e(x.evidence)}</div><p>${e(x.summary||'原文未提供摘要')}</p><small class="muted">${e(x.verification)}</small></article>`).join('')||'<p>本期没有符合筛选的条目。</p>'}q.oninput=dom.onchange=cat.onchange=render;render();document.getElementById('sources').innerHTML='<ul>'+d.sources.map(x=>`<li>${e(x.name)}：${x.ok?'成功':'失败'}，本周 ${x.weekly} 条 ${e(x.error||'')}</li>`).join('')+'</ul><p>'+d.gaps.map(e).join('<br>')+'</p><h3>无发布日期：'+d.undated.length+' 条</h3>'+d.undated.map(x=>`<p><a href="${e(x.url)}">${e(x.title)}</a> · ${e(x.source)}</p>`).join('');
</script></html>'''


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def publish_local(report, root=ROOT):
    day = report['windowEnd'][:10]
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    for name in (day, 'latest'):
        atomic(root / 'reports' / (name + '.json'), encoded)
        atomic(root / 'reports' / (name + '.md'), markdown(report))
    history = sorted(p.stem for p in (root / 'reports').glob('????-??-??.md'))[::-1]
    atomic(root / 'site/index.html', webpage(report, history))
    atomic(root / 'reports/index.json', json.dumps(history))


def check(root=ROOT):
    r = json.loads((root / 'reports/latest.json').read_text(encoding='utf-8'))
    assert r['sources'] and any(s['ok'] for s in r['sources']), '所有源失败'
    start, end = timestamp(r['windowStart']), timestamp(r['windowEnd'])
    assert end - start == timedelta(days=7)
    ids = set()
    for x in r['items']:
        assert start < timestamp(x['publishedAt']) <= end
        assert safe_url(x['url']) and x['id'] not in ids
        ids.add(x['id'])
    assert (root / 'site/index.html').exists() and (root / 'reports/latest.md').exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--now')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if args.check:
        check()
        print('Report checks passed.')
        return 0
    end = timestamp(args.now) if args.now else datetime.now(CST)
    if end is None:
        ap.error('--now 必须含时区')
    end = end.astimezone(CST)
    sources = json.loads((ROOT / 'config/sources.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch_source, sources))
    for s, rows, error in results:
        print(f"{s['name']}: {error or str(len(rows)) + ' items'}")
    if not results or all(error for _, _, error in results):
        print('All sources failed; previous reports preserved.', file=sys.stderr)
        return 1
    report = assemble(results, end)
    publish_local(report)
    check()
    print(f"Published locally: {len(report['items'])} weekly items, {report['status']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
