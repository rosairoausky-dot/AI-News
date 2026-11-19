import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import agent
from sync_workbench import sync

class WorkbenchSyncTests(unittest.TestCase):
    def test_weekly_news_updates_without_optional_feeds(self):
        root=Path(__file__).resolve().parents[1]
        app=(root/'workbench/ai-frontier-atlas.html').read_text(encoding='utf-8')
        report=json.loads((root/'reports/latest.json').read_text(encoding='utf-8'))
        report['generatedAt']='2030-01-01T14:10:00+08:00'
        with TemporaryDirectory() as td:
            result=sync(app,report,Path(td))
        def payload(s):return json.loads(re.search(r'id="researchSnapshot" type="application/json">(.*?)</script>',s,re.S).group(1))
        self.assertEqual(payload(result)['news']['generatedAt'],report['generatedAt'])
        self.assertEqual(payload(result)['rankings'],payload(app)['rankings'])
        self.assertEqual(payload(result)['media'],payload(app)['media'])
        self.assertEqual(result.count('async function refreshPublishedNews'),1)

    def test_new_model_domains_classified(self):
        source={'name':'official','url':'https://example.com','domains':[]}
        for domain,title in [('llm','Claude large language model'),('code','code generation model'),('robotics','vision-language-action robotics')]:
            self.assertIn(domain,agent.classify({'title':title,'summary':'','url':'https://example.com/a'},source)['domains'])

if __name__=='__main__':unittest.main()
