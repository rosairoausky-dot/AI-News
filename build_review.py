"""Build a self-contained review HTML and the public Pages bundle."""
from pathlib import Path
import html
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent

def build():
    output = ROOT / 'public'
    output.mkdir(exist_ok=True)
    skill = (ROOT/'skills/ai-frontier-research/SKILL.md').read_text(encoding='utf-8')
    agent = (ROOT/'agent.md').read_text(encoding='utf-8')
    app = (ROOT/'workbench/ai-frontier-atlas.html').read_text(encoding='utf-8')
    news = (ROOT/'site/index.html').read_text(encoding='utf-8')
    report = json.loads((ROOT/'reports/latest.json').read_text(encoding='utf-8'))
    counts = {d:len(re.findall('domain: "'+d+'"',app)) for d in ['video','music','world']}
    payload = json.dumps({'skill':skill,'agent':agent,'app':app,'news':news},ensure_ascii=False).replace('<','\\u003c')
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Frontier · 审核工作台</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c151d;color:#e8f1f4;font:15px/1.65 system-ui}header{padding:34px 5vw;background:linear-gradient(110deg,#153747,#162333);border-bottom:1px solid #39525f}h1{font-size:34px;margin:8px 0}h2{font-size:22px}p{max-width:950px}small,.muted{color:#a9bec8}nav{position:sticky;top:0;background:#101f2b;padding:12px 5vw;display:flex;gap:9px;flex-wrap:wrap;z-index:5}button,a.button{font:inherit;border:1px solid #45606f;background:#1a3040;color:#e6f3f5;padding:8px 14px;border-radius:9px;cursor:pointer;text-decoration:none}button.active{background:#76e0ca;color:#102b2d}main{padding:22px 5vw}a{color:#7bdecf}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:#162632;border:1px solid #344b59;padding:20px;border-radius:14px}.card strong{display:block;font-size:30px;color:#7bdecf}.warn{border-left:4px solid #f0be6b;background:#332d23;padding:16px;color:#f5d6a7;margin:18px 0}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:14px;border-bottom:1px solid #344b59;vertical-align:top}th{color:#7bdecf}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.9 system-ui;background:#152632;padding:24px;border-radius:14px}iframe{width:100%;height:78vh;background:#111;border:1px solid #45606f;border-radius:12px}.tools{display:flex;gap:12px;margin:15px 0;flex-wrap:wrap}input,select,textarea{background:#142a38;border:1px solid #45606f;border-radius:8px;color:#eef8ff;padding:10px;font:inherit}textarea{width:100%;min-height:130px}input{min-width:240px}[hidden]{display:none!important}.step{padding:18px;border:1px solid #344b59;border-radius:12px;margin:12px 0}summary{cursor:pointer;color:#7bdecf}@media(max-width:700px){h1{font-size:26px}main{padding:15px}td,th{padding:8px;font-size:13px}}
</style></head><body><header><small>AI FRONTIER / REVIEW BEFORE PUBLISH</small><h1>先审核，再发布</h1><p>AI 视频 · AI 音乐 · 世界模型。这里提供完整 Skill、Agent 规范和实际页面预览，并公开当前实现缺口。</p><small>审核版：2026-11-17 · 静态预览可离线打开 · 本轮没有向 GitHub 推送</small></header><nav>
<button data-tab="overview" class="active">需求与完成度</button><button data-tab="skill">完整 Skill</button><button data-tab="agent">Agent 规范</button><button data-tab="app">交互工作台</button><button data-tab="news">行业动态</button><button data-tab="publish">GitHub 发布步骤</button><button data-tab="feedback">审核意见</button></nav><main>
<section id="overview"><h2>当前版本，实事求是</h2><div class="cards">COUNTS</div><div class="warn">当前不是“全部要求完成”的成品。Skill 已覆盖核心需求，但项目覆盖、关系图谱、社媒持续监控以及部分交互验收仍需补齐。GitHub Pages 只托管静态 HTML，不能运行本地 Python 服务。</div><table><thead><tr><th>你的要求</th><th>当前情况</th><th>如何检查</th></tr></thead><tbody>
<tr><td>国内外公司、创业项目与产品全面</td><td>部分完成：现有 20 个项目快照，不能称为全面；版本和人员资料未全面复核。</td><td>打开工作台，按三领域筛选；反馈遗漏公司。</td></tr>
<tr><td>算法负责人、核心人员、论文关系</td><td>已有文字档案和链接；角色证据不够完整，可点击关系图谱尚未实现。</td><td>项目详情与论文页，检查任职和作者来源。</td></tr>
<tr><td>页面内动态、实时社媒采集</td><td>公开源有真实检索记录；社媒扩展仅手动采集，未实现全部账号持续监控。</td><td>行业动态查看摘要与来源；不能把动画视作实时成功。</td></tr>
<tr><td>行业动态按周检索，周四发布</td><td>流水线和配置已实现，本地测试通过；远端部署及定时生效仍待验证。</td><td>查看周报及下方发布步骤。</td></tr>
<tr><td>具体文字颜色、双击循环</td><td>已实现文字选区标注代码；需你在实际页面验收中文、跨节点选区及重开恢复。</td><td>选择词语看浮动色板，双击已标注文字切色。</td></tr>
<tr><td>项目内备注可隐藏</td><td>已实现折叠与同步，未在本轮做完整浏览器回归。</td><td>输入备注后折叠，再展开，切换项目核对。</td></tr>
<tr><td>保存到本地、防丢失</td><td>本地服务支持状态文件及备份；静态网页需要主动导出，预览内更改不等于磁盘保存。</td><td>下载完整包，用启动器运行；以保存状态提示为准。</td></tr>
</tbody></table><h2>优先审核的交互</h2><ol><li>领域/公司/关键词筛选是否清晰。</li><li>文字标注是否仅改变选中文字。</li><li>备注折叠后是否真正隐藏，展开内容是否保留。</li><li>新闻是否直接展示内容、原文、日期和来源失败信息。</li><li>本地保存是否能在关闭并重新打开后恢复。</li></ol></section>
<section id="skill" hidden><h2>完整 Skill · 原文</h2><div class="tools"><input id="findSkill" placeholder="查找关键词，如：核心人员、隐藏"><button id="searchSkill">查找</button><span id="findResult"></span></div><pre id="skillText"></pre></section>
<section id="agent" hidden><h2>Agent 执行规范 · 原文</h2><pre id="agentText"></pre></section>
<section id="app" hidden><h2>交互工作台预览</h2><div class="warn">嵌入预览用于检查筛选、颜色和备注。此处不连接本地采集服务；刷新前请导出重要数据。真实磁盘保存应使用完整包的本地启动器。</div><div class="tools"><a class="button" href="workbench/ai-frontier-atlas.html" target="_blank">打开独立工作台（解压包）</a></div><iframe id="appFrame" title="AI研究工作台" sandbox="allow-scripts allow-downloads allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer"></iframe></section>
<section id="news" hidden><h2>行业动态 · 最近一次已生成报告</h2><p class="muted">REPORT_DATE · 不冒充今日更新。自动分类和来源摘录需原文核验。</p><iframe id="newsFrame" title="行业动态" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer"></iframe></section>
<section id="publish" hidden><h2>重新发布：建议新建“仓库”，不是单个文件</h2><p>先审核此版本。以下步骤不需要把密码、Token 或配对码发给我。新仓库名称可用 <b>ai-frontier-agent</b>。</p>
<div class="step"><b>1 · 解压发布包</b><p>下载本次 ZIP 并解压。进入包含 README.md、agent.py、.github、site、skills、workbench 的目录。不要把 ZIP 本身上传当作网站。</p></div>
<div class="step"><b>2 · 创建空仓库</b><p>GitHub 右上角 + → New repository。选择账号，填写仓库名，建议 Public 方便免费 Pages；不勾选初始化 README、.gitignore、License，然后 Create repository。请把新的仓库 URL 发给我。</p></div>
<div class="step"><b>3 · 用 GitHub Desktop 上传，避免反复设备码</b><p>安装并登录 GitHub Desktop 官方客户端，File → Clone repository → URL，填入新仓库地址并选择空目录。把发布包内所有内容（包括隐藏的 .github 文件夹）复制到克隆目录。填写提交说明 → Commit to main → Publish branch / Push origin。不要复制旧目录里的 .git 或私人 data 文件。</p></div>
<div class="step"><b>4 · 配置 GitHub Pages</b><p>仓库 Settings → Pages → Build and deployment → Source 选择 <b>GitHub Actions</b>。Settings → Actions → General → Workflow permissions 选择 <b>Read and write permissions</b> 并保存，以允许每周提交报告。</p></div>
<div class="step"><b>5 · 首次发布 HTML</b><p>仓库 Actions → 发布行业动态 HTML → Run workflow → 选择 main。等待所有步骤变绿。Settings → Pages 会显示实际网站 URL，格式一般为 https://账号.github.io/仓库名/ 。第一次首页是本审核入口，含工作台和行业动态。</p></div>
<div class="step"><b>6 · 验证每周更新</b><p>Actions → 每周四行业动态 → Run workflow。确认报告提交出现，随后 Pages 部署成功。日后每周四北京时间 09:00 计划运行（GitHub 可能延迟）；无需本机开机。不要把“上传了 yml”当成已运行成功。</p></div>
<div class="step"><b>7 · 故障定位</b><p>404：看 Pages 是否配置为 Actions、部署是否成功。403：检查 workflow 写权限及分支保护。没有运行入口：检查 .github/workflows 是否在默认分支。全源失败：工作流会失败并保留上次报告。公开页面无法启动 Python：正常，需本地启动器。</p></div></section>
<section id="feedback" hidden><h2>审核意见 · 导出到本地文件</h2><p>这里只记录本次审核，不替代项目备注。请点“导出审核意见”，页面刷新会清除尚未导出的内容。</p><label>审核结论 <select id="decision"><option>需要修改后再发布</option><option>可发布审核版，保留缺口说明</option></select></label><p><textarea id="comments" placeholder="请写需要补充的公司/产品、人物信息、动态来源或交互问题…"></textarea></p><button id="exportReview">导出审核意见 JSON</button><span id="saved"></span></section>
</main><script id="payload" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('payload').textContent);document.getElementById('skillText').textContent=data.skill;document.getElementById('agentText').textContent=data.agent;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('main>section').forEach(s=>s.hidden=s.id!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(t=>t.classList.toggle('active',t===b));const id=b.dataset.tab;if(id==='app'&&!document.getElementById('appFrame').srcdoc)document.getElementById('appFrame').srcdoc=data.app;if(id==='news'&&!document.getElementById('newsFrame').srcdoc)document.getElementById('newsFrame').srcdoc=data.news;});
document.getElementById('searchSkill').onclick=()=>{const q=document.getElementById('findSkill').value.trim(),pre=document.getElementById('skillText');pre.textContent=data.skill;if(!q)return;const parts=data.skill.split(q);pre.textContent='';parts.forEach((p,i)=>{if(i){const m=document.createElement('mark');m.textContent=q;pre.append(m)}pre.append(document.createTextNode(p))});document.getElementById('findResult').textContent=(parts.length-1)+' 处匹配';pre.querySelector('mark')?.scrollIntoView({block:'center'});};
document.getElementById('exportReview').onclick=()=>{const blob=new Blob([JSON.stringify({reviewedAt:new Date().toISOString(),decision:document.getElementById('decision').value,comments:document.getElementById('comments').value},null,2)],{type:'application/json'});const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='ai-frontier-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);document.getElementById('saved').textContent=' 已发起下载，请确认本地下载文件。';};
</script></body></html>'''
    cards = ''.join(f'<div class="card">{label}<strong>{value}</strong></div>' for label,value in [('AI 视频项目',counts['video']),('AI 音乐项目',counts['music']),('世界模型项目',counts['world']),('最近周报候选条目',len(report['items']))])
    page = page.replace('COUNTS',cards).replace('REPORT_DATE',html.escape(report['generatedAt'])).replace('PAYLOAD',payload)
    (output/'index.html').write_text(page,encoding='utf-8')
    for name in ['site','reports']:
        shutil.copytree(ROOT/name,output/name,dirs_exist_ok=True)
    (output/'workbench').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'workbench/ai-frontier-atlas.html',output/'workbench/ai-frontier-atlas.html')
    shutil.copy2(ROOT/'workbench/ai-frontier-atlas.html',output/'workbench/index.html')
    (output/'.nojekyll').write_text('')
    print('Built public/index.html and public-only static assets')

if __name__=='__main__':
    build()
