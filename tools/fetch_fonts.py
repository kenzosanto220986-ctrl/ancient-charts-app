"""Download Noto font subsets (greek, latin, latin-ext, symbols) once so the app self-hosts fonts (no third-party requests at runtime)."""
import re, urllib.request, hashlib, pathlib
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
css_url='https://fonts.googleapis.com/css2?family=Noto+Serif:wght@400;600;700&family=Noto+Sans:wght@400;600&family=Noto+Sans+Symbols&family=Noto+Sans+Symbols+2&display=swap'
out=pathlib.Path(__file__).resolve().parent.parent/'static/fonts'; out.mkdir(parents=True,exist_ok=True)
css=urllib.request.urlopen(urllib.request.Request(css_url,headers={'User-Agent':UA})).read().decode()
blocks=re.findall(r'(?:/\*\s*(.*?)\s*\*/\s*)?@font-face\s*\{(.*?)\}',css,re.S)
keep=[];res=[]
for label,b in blocks:
    fam=re.search(r"font-family:\s*'([^']+)'",b).group(1)
    if 'Symbols' not in fam and label not in('greek','latin','latin-ext'): continue
    url=re.search(r'url\((.*?)\)',b).group(1)
    fn=hashlib.md5(url.encode()).hexdigest()[:10]+'.woff2'
    if not (out/fn).exists(): (out/fn).write_bytes(urllib.request.urlopen(url).read())
    res.append(b.replace(url,fn).replace('url(','url(').strip())
(out/'fonts.css').write_text('\n'.join('@font-face {\n  '+re.sub(r'\n\s*','\n  ',r)+'\n}' for r in res))
print(len(res),'faces')
