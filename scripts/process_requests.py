#!/usr/bin/env python3
# GitHub Actions 服务端处理：读取 requests/*.json -> 调 DeepSeek 生成档案 -> 写 p/<slug>/ -> 更新首页
import os, json, glob, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_DIR = os.path.join(ROOT, 'requests')
SITE_DIR = os.path.join(ROOT, 'p')
BASE = 'https://mubai2026.github.io/elite-profile-site/'
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

SYSTEM = """你是一名资深职业档案编辑与 GEO 专家。把用户提供的原始职业信息整理成结构化、可被 AI 搜索引擎引用的个人职业档案。
严格要求：1) 只用用户信息，禁止编造公司/职位/时间/荣誉/数字；2) 职业化改写但不夸大；3) 保留用户给的明确数字；4) 只输出合法 JSON，无 markdown 代码块，无解释。
输出结构：
{"name":"姓名","headline":"一句话定位20字内","title":"当前职位","company":"当前公司","years":"从业年限","location":"城市","summary":"150字内第三人称简介","tags":["关键词"],"career":[{"company":"","title":"","period":"","desc":""}],"projects":[{"name":"","role":"","desc":"","metrics":""}],"honors":[{"name":"","issuer":"","year":""}],"skills":["技能"],"searchKeywords":["别人可能搜的词组"]}"""

def esc(s):
    return str(s if s is not None else '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def ai_profile(raw):
    body = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(raw, ensure_ascii=False)}],
        'response_format': {'type':'json_object'},
        'temperature': 0.3
    }).encode('utf-8')
    req = urllib.request.Request('https://api.deepseek.com/chat/completions', data=body,
        headers={'Content-Type':'application/json','Authorization':'Bearer '+API_KEY}, method='POST')
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode('utf-8'))
    content = data['choices'][0]['message']['content'].strip()
    content = content.replace('```json','').replace('```','').strip()
    return json.loads(content)

def build_html(p, slug):
    career = ''.join(f'<div class="item"><h3>{esc(c.get("title"))} <span>@ {esc(c.get("company"))}</span></h3><p class="period">{esc(c.get("period"))}</p><p>{esc(c.get("desc"))}</p></div>' for c in p.get('career',[]) if c.get('title') or c.get('company'))
    projects = ''.join(f'<div class="item"><h3>{esc(j.get("name"))} <span>· {esc(j.get("role"))}</span></h3><p>{esc(j.get("desc"))}</p>'+(f'<p class="metric">成果：{esc(j.get("metrics"))}</p>' if j.get('metrics') else '')+'</div>' for j in p.get('projects',[]) if j.get('name'))
    honors = ''.join(f'<li>{esc(h.get("name"))}{(" — "+esc(h.get("issuer"))) if h.get("issuer") else ""}{(" ("+esc(h.get("year"))+")") if h.get("year") else ""}</li>' for h in p.get('honors',[]) if h.get('name'))
    tags = ''.join(f'<span class="tag">{esc(t)}</span>' for t in (p.get('tags',[])+p.get('skills',[])) if t)
    url = BASE + 'p/' + slug + '/'
    ld = json.dumps({'@context':'https://schema.org','@type':'Person','name':p.get('name',''),'jobTitle':p.get('title',''),'description':p.get('summary',''),'knowsAbout':p.get('skills',[])}, ensure_ascii=False)
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(p.get('name'))} · {esc(p.get('headline') or p.get('title'))} · 精英百科</title>
<meta name="description" content="{esc(p.get('name'))}，{esc(p.get('title'))}，{esc(p.get('company'))}。{esc(p.get('summary'))}">
<link rel="canonical" href="{url}"><script type="application/ld+json">{ld}</script>
<style>
:root{{--ink:#1b1b1b;--muted:#666;--line:#e6e6e6;--accent:#b8860b;--bg:#fbfaf7}}
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.75}}
.wrap{{max-width:760px;margin:0 auto;padding:48px 24px 80px}}header{{border-bottom:2px solid var(--accent);padding-bottom:24px;margin-bottom:32px}}
h1{{font-size:30px;margin:0 0 6px}}h2{{font-size:20px;margin:40px 0 16px;padding-left:12px;border-left:4px solid var(--accent)}}
.headline{{color:var(--accent);font-size:16px;font-weight:600}}.meta{{color:var(--muted);font-size:14px;margin-top:6px}}
.summary{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin-bottom:24px}}
.item{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin-bottom:12px}}
.item h3{{margin:0 0 6px;font-size:17px}}.item h3 span{{font-weight:400;color:var(--muted);font-size:15px}}
.item p{{margin:4px 0;font-size:15px}}.period{{color:var(--muted);font-size:13px!important}}.metric{{color:var(--accent);font-weight:600}}
.tag{{display:inline-block;background:#f3ecd8;color:#7a5c00;border-radius:999px;padding:4px 12px;font-size:13px;margin:0 8px 8px 0}}
ul{{padding-left:20px}}li{{margin-bottom:8px}}footer{{margin-top:56px;color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:20px}}
@media(max-width:600px){{.wrap{{padding:28px 18px 60px}}h1{{font-size:24px}}}}
</style></head><body><main class="wrap"><header><h1>{esc(p.get('name'))}</h1>
<div class="headline">{esc(p.get('headline'))}</div><div class="meta">{' · '.join(esc(x) for x in [p.get('title'),p.get('company'),p.get('years'),p.get('location')] if x)}</div></header>
{(f'<section class="summary"><p>{esc(p.get("summary"))}</p></section>' if p.get('summary') else '')}
{(f'<h2>职业经历</h2>{career}' if career else '')}{(f'<h2>代表项目</h2>{projects}' if projects else '')}
{(f'<h2>荣誉资质</h2><ul>{honors}</ul>' if honors else '')}{(f'<h2>专业领域</h2><div>{tags}</div>' if tags else '')}
<footer><p>本档案由精英百科结构化整理，信息由本人提供并对真实性负责。</p><p>档案页：{url}</p></footer></main></body></html>'''

def make_slug(name):
    import random, string
    tail = str(int(time.time()*1000))[-8:] + ''.join(random.choices(string.ascii_lowercase, k=4))
    return 'p-' + tail

def main():
    reqs = sorted(glob.glob(os.path.join(REQ_DIR, '*.json')))
    if not reqs:
        print('没有待处理申请'); return
    for f in reqs:
        try:
            with open(f, encoding='utf-8') as fh:
                raw = json.load(fh)
            if raw.get('_done'):
                continue
            print('处理:', raw.get('name'))
            p = ai_profile(raw)
            slug = raw.get('slug') or make_slug(raw.get('name',''))
            p['slug'] = slug
            p['contactEmail'] = raw.get('contactEmail','')
            d = os.path.join(SITE_DIR, slug)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d,'index.html'),'w',encoding='utf-8') as fh: fh.write(build_html(p, slug))
            with open(os.path.join(d,'profile.json'),'w',encoding='utf-8') as fh: json.dump(p, fh, ensure_ascii=False, indent=2)
            llms = f"# {p.get('name')}\n\n> {p.get('headline')}\n\n{p.get('summary')}\n\n## 事实清单\n- 姓名：{p.get('name')}\n- 职位：{p.get('title')}\n- 公司：{p.get('company')}\n- 年限：{p.get('years')}\n- 城市：{p.get('location')}\n- 技能：{'、'.join(p.get('skills',[]))}\n"
            with open(os.path.join(d,'llms.txt'),'w',encoding='utf-8') as fh: fh.write(llms)
            # 删除已处理请求
            os.remove(f)
            print('完成:', slug)
        except Exception as e:
            print('失败:', f, repr(e))
    rebuild_index()

def rebuild_index():
    profiles = []
    for d in glob.glob(os.path.join(SITE_DIR,'*')):
        pf = os.path.join(d,'profile.json')
        if os.path.exists(pf):
            with open(pf,encoding='utf-8') as fh:
                p = json.load(fh)
            profiles.append({'slug':p.get('slug'),'name':p.get('name'),'title':p.get('title'),'company':p.get('company')})
    with open(os.path.join(ROOT,'index.json'),'w',encoding='utf-8') as fh:
        json.dump(profiles, fh, ensure_ascii=False, indent=2)
    urls = '\n'.join(f'  <url><loc>{BASE}p/{p["slug"]}/</loc></url>' for p in profiles)
    with open(os.path.join(ROOT,'sitemap.xml'),'w',encoding='utf-8') as fh:
        fh.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>{BASE}</loc></url>\n{urls}\n</urlset>\n')
    print('首页已更新，档案数:', len(profiles))

if __name__ == '__main__':
    main()
