import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location('agent', Path(__file__).resolve().parents[1] / 'agent.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class AgentTests(unittest.TestCase):
    def test_rss_atom_and_dates(self):
        rss = b'<rss><channel><item><title>AI video release</title><link>https://example.com/a</link><description>&lt;b&gt;Hello&lt;/b&gt;</description><pubDate>Thu, 12 Nov 2026 01:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(a.parse_feed(rss)[0]['summary'], 'Hello')
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>World models</title><link href="https://example.com/p"/><published>2026-11-12T09:00:00+08:00</published></entry></feed>'
        self.assertEqual(a.parse_feed(atom)[0]['url'], 'https://example.com/p')
        self.assertIsNone(a.timestamp('2026-11-12T09:00:00'))

    def test_window_dedup_and_missing_date(self):
        end = datetime(2026, 11, 19, 9, tzinfo=a.CST)
        s = {'name': 'test', 'url': 'https://example.com/feed', 'domains': ['video']}
        rows = [{'title': 'Video', 'summary': '', 'url': 'https://example.com/' + name, 'publishedAt': dt} for name, dt in [('old', (end-timedelta(days=7)).isoformat()), ('valid', (end-timedelta(days=1)).isoformat()), ('future', (end+timedelta(days=1)).isoformat()), ('missing', None)]]
        rows.append(dict(rows[1], url='https://example.com/valid?utm_source=test'))
        r = a.assemble([(s, rows, None), ({**s, 'name': 'failed'}, [], 'timeout')], end)
        self.assertEqual(len(r['items']), 1)
        self.assertEqual(len(r['undated']), 1)
        self.assertEqual(r['status'], 'partial')
        with tempfile.TemporaryDirectory() as td:
            a.publish_local(r, Path(td))
            a.check(Path(td))
            self.assertTrue((Path(td) / 'reports/2026-11-19.md').exists())

    def test_html_injection_and_urls(self):
        self.assertFalse(a.safe_url('javascript:alert(1)'))
        self.assertFalse(a.safe_url('https://user:password@example.com/'))
        r = a.assemble([({'name': 'fixture', 'url': 'https://example.com', 'domains': ['video']}, [{'title': '</script><img src=x onerror=alert(1)>', 'summary': '<b>Video</b>', 'url': 'https://example.com/a', 'publishedAt': '2026-11-18T09:00:00+08:00'}], None)], datetime(2026,11,19,9,tzinfo=a.CST))
        page = a.webpage(r, [])
        self.assertNotIn('</script><img', page)
        self.assertIn('\\u003c/script', page)

    def test_all_sources_fail_keeps_previous_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'config').mkdir()
            (root/'config/sources.json').write_text('[{"name":"offline","url":"https://example.com"}]')
            (root/'reports').mkdir()
            previous = root/'reports/latest.md'
            previous.write_text('Previous report')
            with patch.object(a, 'ROOT', root), patch.object(a, 'fetch_source', side_effect=lambda s: (s, [], 'offline')), patch('sys.argv', ['agent.py']):
                self.assertEqual(a.main(), 1)
            self.assertEqual(previous.read_text(), 'Previous report')


if __name__ == '__main__':
    unittest.main()
