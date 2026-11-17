"""Local research atlas. Python 3.10+, standard library only."""
import concurrent.futures
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
STORE = Path(os.environ.get('ATLAS_DATA_DIR', ROOT / 'data')).resolve()
STORE.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get('ATLAS_PORT', '8765'))
LOCK = threading.RLock()
FETCH_LOCK = threading.Lock()
STATE = STORE / 'state.json'
NEWS = STORE / 'news.json'
CATALOG = STORE / 'catalog.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding='utf-8'))


def atomic(path, value, backup=False):
    encoded = json.dumps(value, ensure_ascii=False, indent=2)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    if backup and path.exists():
        backups = STORE / 'backups'
        backups.mkdir(exist_ok=True)
        target = backups / ('state-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
        shutil.copy2(path, target)
        for old in sorted(backups.glob('state-*.json'))[:-100]:
            old.unlink()
    os.replace(tmp, path)


TOKEN_FILE = STORE / 'pair.json'
if not TOKEN_FILE.exists():
    atomic(TOKEN_FILE, {'token': secrets.token_urlsafe(32)})
TOKEN = read(TOKEN_FILE, {})['token']

SOURCES = [
    {'name': 'Google AI 官方博客', 'channel': '官网/Blog', 'kind': 'rss', 'url': 'https://blog.google/technology/ai/rss/'},
    {'name': 'OpenAI 官方新闻', 'channel': '官网/Blog', 'kind': 'rss', 'url': 'https://openai.com/news/rss.xml'},
    {'name': 'Hugging Face 官方博客', 'channel': '官网/Blog', 'kind': 'rss', 'url': 'https://huggingface.co/blog/feed.xml'},
    {'name': 'arXiv 视频生成', 'channel': '论文/arXiv', 'kind': 'rss', 'domain': 'video', 'url': 'https://export.arxiv.org/api/query?search_query=all:%22video%20generation%22&sortBy=submittedDate&sortOrder=descending&max_results=12'},
    {'name': 'arXiv 音乐生成', 'channel': '论文/arXiv', 'kind': 'rss', 'domain': 'music', 'url': 'https://export.arxiv.org/api/query?search_query=all:%22music%20generation%22&sortBy=submittedDate&sortOrder=descending&max_results=12'},
    {'name': 'arXiv 世界模型', 'channel': '论文/arXiv', 'kind': 'rss', 'domain': 'world', 'url': 'https://export.arxiv.org/api/query?search_query=all:%22world%20model%22&sortBy=submittedDate&sortOrder=descending&max_results=12'},
    {'name': 'Hugging Face 最新视频模型', 'channel': 'Hugging Face', 'kind': 'hf', 'domain': 'video', 'url': 'https://huggingface.co/api/models?pipeline_tag=text-to-video&sort=lastModified&direction=-1&limit=12'},
    {'name': 'Hugging Face 最新音频模型', 'channel': 'Hugging Face', 'kind': 'hf', 'domain': 'music', 'url': 'https://huggingface.co/api/models?pipeline_tag=text-to-audio&sort=lastModified&direction=-1&limit=12'},
    {'name': 'Wan 视频模型 GitHub', 'channel': 'GitHub', 'kind': 'github', 'domain': 'video', 'url': 'https://api.github.com/repos/Wan-Video/Wan2.2/commits?per_page=8'},
    {'name': '腾讯混元视频 GitHub', 'channel': 'GitHub', 'kind': 'github', 'domain': 'video', 'url': 'https://api.github.com/repos/Tencent-Hunyuan/HunyuanVideo/commits?per_page=8'},
    {'name': 'AudioCraft GitHub', 'channel': 'GitHub', 'kind': 'github', 'domain': 'music', 'url': 'https://api.github.com/repos/facebookresearch/audiocraft/commits?per_page=8'},
    {'name': 'NVIDIA Cosmos GitHub', 'channel': 'GitHub', 'kind': 'github', 'domain': 'world', 'url': 'https://api.github.com/repos/nvidia-cosmos/cosmos-predict2/commits?per_page=8'},
]
SOURCE_FILE = STORE / 'sources.json'
if not SOURCE_FILE.exists():
    atomic(SOURCE_FILE, SOURCES)


def clean(value):
    value = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', value or '', flags=re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', value))).strip()


def date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(value).isoformat()
        except (ValueError, TypeError):
            return None


def classify(item, catalog):
    corpus = (' '.join(str(item.get(k, '')) for k in ('title', 'summary', 'url', 'source'))).lower()
    ids = set(item.get('projectIds', []))
    domains = set(item.get('domains', []))
    for p in catalog:
        parts = re.split(r'[/·]|\s+-\s+', p.get('project', '') + '/' + p.get('company', ''))
        parts += re.findall(r'[A-Za-z][A-Za-z0-9-]{3,}|[\u4e00-\u9fff]{2,}', p.get('project', ''))
        blocked = {'video', 'music', 'world', 'model', 'models', 'research', 'google', 'meta', 'labs', 'open', 'generator', 'licensed', 'intelligence'}
        if any(len(x.strip()) > 2 and x.strip().lower() not in blocked and x.strip().lower() in corpus for x in parts):
            ids.add(p['id'])
            domains.add(p['domain'])
    for domain, terms in {'video': ['video', '视频', 'sora', 'veo', 'kling', 'seedance'], 'music': ['music', 'audio', '音乐', '音频', 'suno', 'udio'], 'world': ['world model', '世界模型', 'cosmos', 'genie', 'spatial', 'robot', '机器人', '3d world', 'v-jepa']}.items():
        if any(t in corpus for t in terms):
            domains.add(domain)
    item['projectIds'] = sorted(ids)
    item['domains'] = sorted(domains)
    return item


def parse_rss(raw):
    root = ET.fromstring(raw)
    entries = [e for e in root.iter() if e.tag.split('}')[-1] in ('item', 'entry')]
    result = []
    for e in entries[:30]:
        values = {}
        link = ''
        for child in e:
            name = child.tag.split('}')[-1]
            values[name] = ''.join(child.itertext())
            if name == 'link' and (child.attrib.get('rel', 'alternate') == 'alternate'):
                link = child.attrib.get('href') or child.text or ''
        title = clean(values.get('title', ''))
        if title and link.startswith(('https://', 'http://')):
            result.append({'title': title, 'url': link.strip(), 'summary': clean(values.get('description') or values.get('summary') or values.get('encoded', ''))[:3000], 'publishedAt': date(values.get('pubDate') or values.get('published') or values.get('updated'))})
    return result


def collect(source):
    checked = now()
    try:
        req = Request(source['url'], headers={'User-Agent': 'AIFrontierAtlas/2.0 (local research reader)', 'Accept': 'application/json, application/atom+xml, application/rss+xml, text/xml;q=0.9, */*;q=0.5'})
        with urlopen(req, timeout=20) as resp:
            raw = resp.read(8_000_000)
        kind = source['kind']
        if kind == 'rss':
            items = parse_rss(raw)
        elif kind == 'github':
            items = [{'title': x['commit']['message'].split('\n')[0], 'summary': x['commit']['message'], 'url': x['html_url'], 'publishedAt': date(x['commit']['committer']['date'])} for x in json.loads(raw)]
        elif kind == 'hf':
            items = [{'title': x['id'] + ' · 模型更新', 'url': 'https://huggingface.co/' + x['id'], 'summary': '模型卡元数据：' + ', '.join(x.get('tags', [])[:12]), 'publishedAt': date(x.get('lastModified')), 'version': x.get('sha', '')} for x in json.loads(raw)]
        else:
            raise ValueError('未知采集类型')
        for item in items:
            item.update(channel=source['channel'], source=source['name'], ingestedAt=checked, domains=[source['domain']] if source.get('domain') else [])
            key = item['url'] + (item.get('version', '') if kind == 'hf' else '')
            item['id'] = hashlib.sha256(key.encode()).hexdigest()[:24]
        return items, {'name': source['name'], 'ok': bool(items), 'status': '成功' if items else '未解析到条目', 'detail': f'{len(items)} 条原始结果', 'checkedAt': checked}
    except Exception as exc:
        return [], {'name': source['name'], 'ok': False, 'status': '访问失败', 'detail': str(exc)[:160], 'checkedAt': checked}


def do_fetch():
    if not FETCH_LOCK.acquire(blocking=False):
        return
    try:
        sources = read(SOURCE_FILE, SOURCES)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for items, status in pool.map(collect, sources):
                with LOCK:
                    data = read(NEWS, {'items': [], 'sources': []})
                    catalog = read(CATALOG, [])
                    for item in items:
                        classify(item, catalog)
                    # General corporate RSS is retained only when relevant to the three domains.
                    items = [x for x in items if x['domains']]
                    by_id = {x['id']: x for x in data['items']}
                    for item in items:
                        if item['id'] not in by_id:
                            by_id[item['id']] = item
                    data['items'] = sorted(by_id.values(), key=lambda x: x.get('publishedAt') or x.get('ingestedAt', ''), reverse=True)[:5000]
                    status['detail'] += f'，相关 {len(items)} 条'
                    data['sources'] = [s for s in data['sources'] if s['name'] != status['name']] + [status]
                    data['lastFetch'] = now()
                    atomic(NEWS, data)
    finally:
        FETCH_LOCK.release()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, status=200):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def trusted(self, extension=False):
        if self.headers.get('Host') not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            return False
        if extension:
            return secrets.compare_digest(self.headers.get('X-Atlas-Token', ''), TOKEN)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
            return False
        return self.headers.get('X-Atlas-Request') == '1'

    def body(self):
        n = int(self.headers.get('Content-Length', '0'))
        if not 0 <= n <= 5_000_000:
            raise ValueError('数据过大')
        return json.loads(self.rfile.read(n) or b'{}')

    def do_GET(self):
        try:
            if self.path.startswith('/api/'):
                if not self.trusted():
                    return self.send_json({'error': '本地请求校验失败'}, 403)
                with LOCK:
                    if self.path == '/api/state':
                        value = read(STATE, None)
                        return self.send_json({'state': value, 'revision': (value or {}).get('revision', 0)})
                    if self.path == '/api/pair':
                        return self.send_json({'token': TOKEN})
                    if self.path == '/api/news':
                        value = read(NEWS, {'items': [], 'sources': []})
                        for channel in ['X/Twitter', '小红书', '微信公众号']:
                            if not any(s['name'] == channel for s in value['sources']):
                                value['sources'].append({'name': channel, 'ok': False, 'status': '等待登录采集', 'detail': '在配套扩展中启用当前页面采集'})
                        value['fetching'] = FETCH_LOCK.locked()
                        return self.send_json(value)
                return self.send_json({'error': '不存在'}, 404)
            route = self.path.split('?')[0]
            if route == '/site/index.html':
                page = ROOT.parent / 'site/index.html'
                if not page.exists():
                    return self.send_json({'error': '尚未生成周报，请先运行仓库根目录的 agent.py'}, 404)
                raw = page.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if re.fullmatch(r'/reports/\d{4}-\d{2}-\d{2}\.md', route):
                report = ROOT.parent / route.lstrip('/')
                if not report.exists():
                    return self.send_json({'error': '周报不存在'}, 404)
                raw = report.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if route not in ('/', '/ai-frontier-atlas.html'):
                return self.send_json({'error': '不存在'}, 404)
            raw = (ROOT / 'ai-frontier-atlas.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)
        except Exception as exc:
            self.send_json({'error': str(exc)}, 500)

    def do_PUT(self):
        if not self.trusted():
            return self.send_json({'error': '本地请求校验失败'}, 403)
        try:
            if self.path != '/api/state':
                return self.send_json({'error': '不存在'}, 404)
            value = self.body()
            st = value.get('state')
            if not isinstance(st, dict) or not isinstance(st.get('annotations'), dict) or not isinstance(st.get('updates'), list):
                raise ValueError('状态文件格式无效')
            with LOCK:
                current = read(STATE, {})
                revision = current.get('revision', 0)
                if value.get('revision') != revision:
                    return self.send_json({'error': '另一窗口已更新文件，请导出当前数据后重新加载，避免覆盖', 'revision': revision}, 409)
                st['revision'] = revision + 1
                atomic(STATE, st, backup=True)
            return self.send_json({'revision': revision + 1})
        except Exception as exc:
            self.send_json({'error': str(exc)}, 400)

    def do_POST(self):
        extension = self.path == '/api/ingest'
        if not self.trusted(extension):
            return self.send_json({'error': '配对码或本地请求校验失败'}, 403)
        try:
            if self.path == '/api/refresh':
                threading.Thread(target=do_fetch, daemon=True).start()
                return self.send_json({'started': True})
            if self.path == '/api/catalog':
                catalog = self.body()
                if not isinstance(catalog, list):
                    raise ValueError('catalog 格式无效')
                with LOCK:
                    atomic(CATALOG, catalog)
                    data = read(NEWS, {'items': [], 'sources': []})
                    data['items'] = [classify(x, catalog) for x in data['items']]
                    atomic(NEWS, data)
                return self.send_json({'ok': True})
            if extension:
                payload = self.body()
                channel = payload.get('channel')
                allowed = {'X/Twitter': ['x.com', 'twitter.com'], '小红书': ['www.xiaohongshu.com'], '微信公众号': ['mp.weixin.qq.com']}
                if channel not in allowed:
                    raise ValueError('来源不支持')
                items = []
                for row in payload.get('items', [])[:100]:
                    url = str(row.get('url', ''))
                    if urlparse(url).hostname not in allowed[channel]:
                        continue
                    summary = str(row.get('summary', ''))[:10000]
                    if not summary.strip():
                        continue
                    item = {'id': hashlib.sha256(url.split('?')[0].encode()).hexdigest()[:24], 'channel': channel, 'url': url, 'title': str(row.get('title', ''))[:300], 'summary': summary, 'source': str(row.get('author', channel))[:120], 'publishedAt': date(str(row.get('publishedAt') or '')), 'ingestedAt': now(), 'observedOnly': True}
                    items.append(item)
                with LOCK:
                    data = read(NEWS, {'items': [], 'sources': []})
                    catalog = read(CATALOG, [])
                    by_id = {x['id']: x for x in data['items']}
                    for item in items:
                        # Update visible text when a detail view supplies more than a preview.
                        old = by_id.get(item['id'])
                        if not old or len(item['summary']) > len(old.get('summary', '')):
                            by_id[item['id']] = classify(item, catalog)
                    data['items'] = list(by_id.values())[-5000:]
                    data['sources'] = [s for s in data['sources'] if s['name'] != channel] + [{'name': channel, 'ok': bool(items), 'status': '已采集可见内容' if items else '未读取到内容', 'detail': str(payload.get('status', ''))[:200] + f' · 本次 {len(items)} 条', 'checkedAt': now()}]
                    atomic(NEWS, data)
                return self.send_json({'accepted': len(items)})
            self.send_json({'error': '不存在'}, 404)
        except Exception as exc:
            self.send_json({'error': str(exc)}, 400)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    def schedule():
        while True:
            do_fetch()
            time.sleep(900)
    threading.Thread(target=schedule, daemon=True).start()
    print(f'AI Frontier Atlas: http://127.0.0.1:{PORT}/', flush=True)
    server.serve_forever()
