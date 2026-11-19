"""Replace published news independently of optional ranking/media refreshes."""
import json
import re

def sync(app, report, root):
    pattern=r'(<script id="researchSnapshot" type="application/json">)(.*?)(</script>)'
    match=re.search(pattern,app,re.S)
    if not match:
        raise ValueError('Missing workbench research snapshot; refusing stale deployment')
    snapshot=json.loads(match.group(2))
    snapshot['news']=report
    for key,filename in [('media','media.json'),('rankings','rankings.json')]:
        path=root/'reports'/filename
        if path.exists():snapshot[key]=json.loads(path.read_text(encoding='utf-8'))
    encoded=json.dumps(snapshot,ensure_ascii=False).replace('<','\\u003c')
    app=app[:match.start(2)]+encoded+app[match.end(2):]
    # Existing installations may have no optional published ranking/media files.
    start="    document.getElementById('reloadSnapshot').onclick="
    end="    document.getElementById('sourceStatuses').innerHTML="
    a=app.index(start);b=app.index(end,a)
    app=app[:a]+'''    async function refreshPublishedNews(manual=false){
      const status=document.getElementById('snapshotStatus');
      if(manual)status.textContent='正在读取已发布行业动态…';
      try{
        const base=new URL('../reports/',location.href);
        const r=await fetch(new URL('latest.json?v='+Date.now(),base),{cache:'no-store'});
        if(!r.ok)throw Error('周报 HTTP '+r.status);
        const news=await r.json();
        if(!Array.isArray(news.items)||!news.generatedAt)throw Error('周报格式异常');
        if(Date.parse(news.generatedAt)<Date.parse(RESEARCH.news.generatedAt)){
          status.textContent='已发布周报早于页面内置快照，保留较新内容。';return;
        }
        RESEARCH.news=news;
        generatedNews.splice(0,generatedNews.length,...news.items.map(withProjects));
        document.getElementById('researchSnapshot').textContent=JSON.stringify(RESEARCH).replace(/</g,String.fromCharCode(92)+'u003c');
        renderTicker();renderDrawer();
        document.getElementById('sourceStatuses').innerHTML=news.sources.map(x=>`<div class="source-row"><strong>${escapeHtml(x.name)}</strong><span>${x.ok?'已检索':'未取回'}</span><span>${escapeHtml(x.error||'')}</span></div>`).join('');
        status.textContent='行业动态已同步 '+dateText(news.generatedAt)+'；排行榜与资料库另见各自日期。';
      }catch(e){status.textContent='未取得新周报：'+e.message+'。保留内置快照。';}
    }
    document.getElementById('reloadSnapshot').onclick=()=>refreshPublishedNews(true);
    if(/^https?:$/.test(location.protocol)&&!['localhost','127.0.0.1'].includes(location.hostname)){
      refreshPublishedNews();setInterval(()=>refreshPublishedNews(),300000);
    }
''' +app[b:]
    return app
