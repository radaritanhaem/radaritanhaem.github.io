"""Gera o portal Transparência Itanhaém a partir da pasta conteudo/.

  conteudo/noticias/*.md  -> /noticia/<endereco>      (mesmo endereço do portal antigo)
  conteudo/edicoes/*.md   -> /edicao/<endereco>        (documentos em PDF)
  conteudo/podcasts/*.md  -> /podcast/<endereco>
  conteudo/videos/*.md    -> /video/<endereco>
  conteudo/eventos/*.md   -> /evento/<endereco>
  conteudo/vagas/*.md     -> /vaga-de-emprego/<endereco>
  conteudo/guia/*.md      -> /guia/<endereco>
  + página inicial, /noticias (todas), /noticias/<categoria>, listas, rss.xml, sitemap.xml, 404.html

Cada arquivo .md tem um cabeçalho (entre ---) e o texto em HTML ou Markdown simples.
A seção da Câmara (/camara) é feita por outro programa e não é tocada aqui.

Uso: python gerar_site.py
"""
import datetime as dt, glob, html, json, os, re, unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(RAIZ, "site")
URL = os.environ.get("SITE_URL", "https://www.transparenciaitanhaem.com.br")
PORTAL_ANTIGO = "https://www.transparenciaitanhaem.com.br"
NOME = "Transparência Itanhaém"
TIPOS = {  # pasta: (rota, nome no singular, nome da lista, página da lista)
    "noticias": ("noticia", "Notícia", "Notícias", "noticias"),
    "edicoes": ("edicao", "Documento", "Documentos", "documentos"),
    "podcasts": ("podcast", "Podcast", "Podcasts", "podcasts"),
    "videos": ("video", "Vídeo", "Vídeos", "videos"),
    "eventos": ("evento", "Evento", "Eventos", "eventos"),
    "vagas": ("vaga-de-emprego", "Vaga", "Vagas de emprego", "vagas"),
    "guia": ("guia", "Guia comercial", "Guia comercial", "guia-comercial"),
}
REDES = [("Instagram", "https://www.instagram.com/transparenciaitanhaem_/"), ("Facebook", "https://www.facebook.com/transparenciaitanhaem/"),
         ("YouTube", "https://www.youtube.com/@transparenciaitanhaem"), ("TikTok", "https://www.tiktok.com/@transparenciaitanhaem"),
         ("X", "https://x.com/itanhaem_transp")]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
e = lambda s: html.escape(str(s or ""), quote=True)

def longo(p):
    p = os.path.abspath(p)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p

def slug(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "geral"

def nome_cat(c):
    return c[:1].upper() + c[1:].lower() if c.isupper() else c

def data_br(iso, hora=False):
    if not iso:
        return ""
    d = dt.datetime.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month-1]} de {d.year}" + (f", {d:%H:%M}" if hora else "")

# ---------- leitura ----------
def ler_md(caminho):
    s = open(longo(caminho), encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", s, re.S)
    meta = {}
    try:  # o painel de publicação grava YAML completo (textos longos em várias linhas)
        import yaml
        meta = {k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v)
                for k, v in (yaml.safe_load(m.group(1)) or {}).items()}
        meta = {k: ("" if v is None else v) for k, v in meta.items()}
    except ImportError:
        pass
    for linha in ([] if meta else m.group(1).splitlines()):
        if ":" in linha:
            k, v = linha.split(":", 1); v = v.strip()
            try:
                meta[k.strip()] = json.loads(v) if v.startswith('"') else v
            except json.JSONDecodeError:
                meta[k.strip()] = v.strip('"')
    meta["corpo"] = m.group(2).strip()
    if not meta.get("endereco"):  # notícia nova feita no painel: o endereço é o nome do arquivo
        meta["endereco"] = os.path.splitext(os.path.basename(caminho))[0]
    meta["endereco"] = slug(meta["endereco"])
    return meta

def markdown(t):
    """Markdown simples para notícias novas (o texto antigo já vem em HTML)."""
    if re.match(r"\s*<", t):
        return t
    def inline(x):
        x = e(x)
        x = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', x)
        x = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', x)
        x = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", x)
        return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*", r"<em>\1</em>", x)
    out = []
    for bloco in re.split(r"\n\s*\n", t.strip()):
        b = bloco.strip()
        yt = re.fullmatch(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{6,})\S*", b)
        if yt:
            out.append(f'<iframe src="https://www.youtube.com/embed/{yt.group(1)}" title="Vídeo" allowfullscreen loading="lazy"></iframe>')
        elif re.match(r"#{2,4} ", b):
            n = len(b.split(" ")[0]); out.append(f"<h{n}>{inline(b[n+1:])}</h{n}>")
        elif all(re.match(r"[-*] ", l) for l in b.splitlines()):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in b.splitlines()) + "</ul>")
        elif b.startswith("> "):
            out.append(f"<blockquote>{inline(b[2:])}</blockquote>")
        else:
            out.append("<p>" + "<br>".join(inline(l) for l in b.splitlines()) + "</p>")
    return "\n".join(out)

def preparar_corpo(c):
    c = markdown(c)
    # vídeos grandes ainda não foram para o YouTube: por enquanto tocam do portal antigo
    c = re.sub(r'src="(/uploads/medias/[^"]+\.mp4)"', lambda m: f'src="{PORTAL_ANTIGO}{m.group(1)}"', c)
    c = re.sub(r"<(img|iframe)\b(?![^>]*loading=)", r'<\1 loading="lazy"', c)
    c = re.sub(r'<a href="(https?://(?!www\.transparenciaitanhaem)[^"]+)"(?![^>]*target=)', r'<a href="\1" target="_blank" rel="noopener"', c)
    return c

def carregar():
    itens = []
    for pasta, (rota, *_rest) in TIPOS.items():
        for p in glob.glob(os.path.join(RAIZ, "conteudo", pasta, "*.md")):
            m = ler_md(p)
            if str(m.get("rascunho", "")).lower() in ("true", "sim", "1"):
                continue
            m["pasta"], m["rota"] = pasta, rota
            m["url"] = f"/{rota}/{m['endereco']}"
            m["cat"] = nome_cat(m.get("categoria") or "Geral") if pasta == "noticias" else TIPOS[pasta][1]
            m["cat_slug"] = slug(m["cat"])
            m["data"] = m.get("data") or "2025-01-01T00:00:00-03:00"
            itens.append(m)
    itens.sort(key=lambda x: x["data"], reverse=True)
    return itens

# ---------- pedaços de página ----------
def cabecalho(ativo=""):
    links = [("/", "Início"), ("/noticias", "Notícias"), ("/camara/", "Câmara"), ("/prefeitura/", "Prefeitura"),
             ("/documentos", "Documentos"), ("/podcasts", "Podcasts"), ("/guia-comercial", "Guia")]
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == ativo else ""}>{t}</a>' for h, t in links)
    return f"""<header class="topo-site"><div class="wrap topo-in">
  <a class="logo" href="/" aria-label="{NOME}, página inicial"><img src="/marca/transparencia-itanhaem.png" alt="{NOME}" width="500" height="140"></a>
  <nav class="menu" aria-label="Seções do portal">{nav}</nav></div></header>"""

def rodape():
    redes = " · ".join(f'<a href="{u}" target="_blank" rel="noopener">{n}</a>' for n, u in REDES)
    return f"""<footer class="rodape-site"><div class="wrap">
  <img src="/marca/transparencia-itanhaem.png" alt="{NOME}" width="500" height="140" loading="lazy">
  <p><b>{NOME}</b>: notícias e fiscalização do poder público de Itanhaém-SP. Projeto independente, sem ligação com a Prefeitura, a Câmara ou partidos.</p>
  <p>{redes}</p>
  <p class="muted">Achou um erro? <a href="https://github.com/radaritanhaem/radaritanhaem.github.io/issues" target="_blank" rel="noopener">Avise aqui</a>. Os dados da Câmara e da Prefeitura vêm só de fontes oficiais, com link para cada documento.</p>
</div></footer>"""

def pagina(titulo, corpo, caminho, desc="", imagem="", ativo="", tipo_og="website", extra_head=""):
    canon = URL + (caminho if caminho != "/index" else "/")
    img = (URL + imagem) if imagem.startswith("/") else imagem
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(desc)[:300]}">
<link rel="canonical" href="{e(canon)}">
<meta property="og:site_name" content="{NOME}"><meta property="og:type" content="{tipo_og}">
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(desc)[:300]}"><meta property="og:url" content="{e(canon)}">
{f'<meta property="og:image" content="{e(img)}"><meta name="twitter:card" content="summary_large_image">' if img else ''}
<link rel="icon" href="/marca/icone.webp" type="image/webp">
<link rel="alternate" type="application/rss+xml" title="{NOME}" href="/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800;900&family=Public+Sans:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/assets/estilo.css">{extra_head}
</head><body>
{cabecalho(ativo)}
<main class="wrap">{corpo}</main>
{rodape()}
<script src="/assets/site.js" defer></script>
</body></html>"""

def cartao(m, grande=False):
    capa = f'<img src="{e(m["capa"])}" alt="" loading="lazy">' if m.get("capa") else '<span class="sem-capa"></span>'
    cor = f' style="--cat:{e(m["cor"])}"' if m.get("cor") else ""
    sub = f'<p class="sub">{e(m["subtitulo"])}</p>' if grande and m.get("subtitulo") else ""
    return f"""<article class="cartao{' grande' if grande else ''}"><a href="{e(m['url'])}">
  <div class="capa">{capa}</div>
  <div class="txt"><span class="cat"{cor}>{e(m['cat'])}</span><h3>{e(m['titulo'])}</h3>{sub}<time datetime="{e(m['data'])}">{data_br(m['data'])}</time></div></a></article>"""

def compartilhar(m):
    u = URL + m["url"]
    t = m["titulo"]
    from urllib.parse import quote
    return f"""<div class="compartilhar"><span>Compartilhar:</span>
  <a class="zap" href="https://api.whatsapp.com/send?text={quote(t + ' ' + u)}" target="_blank" rel="noopener">WhatsApp</a>
  <a href="https://www.facebook.com/sharer/sharer.php?u={quote(u)}" target="_blank" rel="noopener">Facebook</a>
  <a href="https://twitter.com/intent/tweet?text={quote(t)}&amp;url={quote(u)}" target="_blank" rel="noopener">X</a>
  <button type="button" data-copiar="{e(u)}">Copiar link</button></div>"""

def pagina_item(m, todos):
    cor = f' style="--cat:{e(m["cor"])}"' if m.get("cor") else ""
    cat_link = f"/noticias/{m['cat_slug']}" if m["pasta"] == "noticias" else "/" + TIPOS[m["pasta"]][3]
    atual = f' · atualizado em {data_br(m["atualizado"], True)}' if m.get("atualizado") and m["atualizado"][:16] != m["data"][:16] else ""
    capa = ""
    if m.get("capa") and m["pasta"] not in ("videos", "podcasts"):
        capa = f'<figure class="capa-materia"><img src="{e(m["capa"])}" alt="" fetchpriority="high"></figure>'
    arquivo = ""
    if m.get("arquivo"):
        arquivo = f"""<p><a class="botao" href="{e(m['arquivo'])}" target="_blank" rel="noopener">Abrir o documento (PDF) ↗</a></p>
<iframe class="pdf" src="{e(m['arquivo'])}" title="{e(m['titulo'])}" loading="lazy"></iframe>"""
    tags = "".join(f'<span class="tag">{e(t.strip())}</span>' for t in (m.get("tags") or "").split(",") if t.strip())
    rel = [x for x in todos if x is not m and x["pasta"] == m["pasta"] and x["cat"] == m["cat"]][:3] or \
          [x for x in todos if x is not m and x["pasta"] == "noticias"][:3]
    corpo = f"""<article class="materia">
<nav class="trilha"><a href="/">Início</a> › <a href="{cat_link}"{cor}>{e(m['cat'])}</a></nav>
<h1>{e(m['titulo'])}</h1>
{f'<p class="linha-fina">{e(m["subtitulo"])}</p>' if m.get('subtitulo') else ''}
<p class="assinatura">Por <b>{e(m.get('autor') or NOME)}</b> · <time datetime="{e(m['data'])}">{data_br(m['data'], True)}</time>{atual}</p>
{compartilhar(m)}
{capa}
<div class="texto">{arquivo}{preparar_corpo(m['corpo'])}</div>
{f'<p class="fonte">Fonte/créditos: {e(m["fonte"])}</p>' if m.get('fonte') else ''}
{f'<div class="tags">{tags}</div>' if tags else ''}
{compartilhar(m)}
</article>
<section class="relacionadas"><h2>Leia também</h2><div class="grade">{''.join(cartao(x) for x in rel)}</div></section>"""
    desc = m.get("subtitulo") or m.get("resumo") or re.sub(r"<[^>]+>", " ", m["corpo"])[:200]
    ld = json.dumps({"@context": "https://schema.org", "@type": "NewsArticle", "headline": m["titulo"], "datePublished": m["data"],
                     "dateModified": m.get("atualizado") or m["data"], "image": [URL + m["capa"]] if m.get("capa") else [],
                     "author": {"@type": "Organization", "name": m.get("autor") or NOME},
                     "publisher": {"@type": "Organization", "name": NOME}}, ensure_ascii=False)
    return pagina(f"{m['titulo']} | {NOME}", corpo, m["url"], desc, m.get("capa", ""), tipo_og="article",
                  extra_head=f'\n<script type="application/ld+json">{ld}</script>')

def pagina_lista(titulo, intro, itens, caminho, ativo="", chips=""):
    corpo = f"""<section class="cab-lista"><h1>{e(titulo)}</h1>{f'<p>{intro}</p>' if intro else ''}{chips}</section>
<div class="grade lista" data-paginar="12">{''.join(cartao(m) for m in itens) or '<p class="muted">Nada publicado ainda.</p>'}</div>"""
    return pagina(f"{titulo} | {NOME}", corpo, caminho, re.sub(r"<[^>]+>", "", intro), ativo=ativo)

def resumo_camara():
    p = os.path.join(SITE, "camara", "dados-site.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    return {"props": len(d["props"]), "salario": d["salario"]["mensal"], "cadeiras": d["salario"]["cadeiras"],
            "folha": (d.get("folha") or {}).get("total_bruto"), "folha_per": f'{(d.get("folha") or {}).get("de","").lower()} a {(d.get("folha") or {}).get("ate","").lower()}',
            "lic": len((d.get("licitacoes") or {}).get("lista", [])), "atualizado": d["atualizado"]}

# ---------- Raio-X da Prefeitura ----------
GRUPOS_PREF = [  # (chave, nome, grupos do coletor) na ordem fixa das cores
    ("pessoal", "Salários e encargos", ["pessoal"]),
    ("servicos", "Serviços e contratos", ["servicos"]),
    ("obras", "Obras e equipamentos", ["obras", "equipamentos"]),
    ("material", "Material", ["material"]),
    ("divida", "Dívidas e ações judiciais", ["divida", "sentencas"]),
    ("outros", "Repasses e outros", ["repasses", "outros"]),
]
MESES_C = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
FORN_NOMES = {"46.578.498/0001-75": "Folha de pagamento dos servidores", "08.424.027/0001-13": "Iprev (previdência dos servidores)",
              "29.979.036/0001-40": "INSS"}

def nome_unidade(u):
    u = re.sub(r"-FDO MUNICIPAL SAÚDE", "", u).strip()
    u = re.sub(r"^SECRETARIA (DE |DA |DO )?", "", u)
    t = u.lower().title()
    for a, b in [(" De ", " de "), (" Da ", " da "), (" Do ", " do "), (" E ", " e "), ("Economico", "Econômico"), ("Relações De", "Relações de")]:
        t = t.replace(a, b)
    return t

def mi(v):  # centavos -> texto curto
    r = v / 100
    if r >= 1e6:
        return f"R$ {r/1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {r/1e3:,.0f} mil".replace(",", ".")

def reais(v):
    return "R$ " + f"{v/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pagina_prefeitura():
    pd = os.path.join(RAIZ, "dados", "prefeitura_despesas.json")
    if not os.path.exists(pd):
        return None
    d = json.load(open(pd, encoding="utf-8"))
    secs = json.load(open(os.path.join(RAIZ, "dados", "prefeitura_secretarios.json"), encoding="utf-8"))
    pc = os.path.join(RAIZ, "dados", "prefeitura_conferencia.json")
    conf = json.load(open(pc, encoding="utf-8")) if os.path.exists(pc) else {}
    import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from prefeitura import casar
    ano, total = d["exercicio"], d["total"]
    meses = sorted(d["meses"])
    unidades = sorted(d["unidades"].items(), key=lambda kv: -kv[1]["tot"])
    maior = unidades[0]
    # meses
    mx = max(d["meses"].values())
    barras_mes = "".join(f"""<div class="col" data-tip="{MESES_C[int(m[5:])-1]}/{m[:4]}: {reais(d['meses'][m])}" tabindex="0">
<span class="v">{mi(d['meses'][m]).replace('R$ ','')}</span><i style="height:{max(2,100*d['meses'][m]/mx):.1f}%"></i><span class="m">{MESES_C[int(m[5:])-1]}</span></div>""" for m in meses)
    # ranking
    ranking = "".join(f"""<li><a href="#s-{slug(u)}"><span class="nm">{e(nome_unidade(u))}</span><span class="v">{mi(x['tot'])}</span></a>
<div class="barra" data-tip="{e(nome_unidade(u))}: {reais(x['tot'])} ({100*x['tot']/total:.1f}% do total)"><i style="width:{100*x['tot']/maior[1]['tot']:.1f}%"></i></div></li>""" for u, x in unidades)
    # cartões
    legenda = "".join(f'<span><i class="sw g{i+1}"></i>{n}</span>' for i, (_, n, _g) in enumerate(GRUPOS_PREF))
    cards = []
    for u, x in unidades:
        s = casar(u, secs)
        pessoa = (f'<b>{e(s["nome"])}</b><span class="muted">{e(s["cargo"])}{" · " + e(s["formacao"]) if s.get("formacao") else ""}</span>'
                  if s and s.get("nome") else '<b class="muted">Não informado no site da Prefeitura</b>')
        link = f' · <a href="{e(s["pagina"])}" target="_blank" rel="noopener">página oficial ↗</a>' if s else ""
        g = d["grupos"].get(u, {})
        comp = [(i, n, sum(g.get(k, 0) for k in ks)) for i, (_, n, ks) in enumerate(GRUPOS_PREF)]
        pilha = "".join(f'<i class="g{i+1}" style="width:{100*v/x["tot"]:.2f}%" data-tip="{n}: {reais(v)} ({100*v/x["tot"]:.0f}%)"></i>' for i, n, v in comp if v > 0)
        tabela = "".join(f'<tr><td><i class="sw g{i+1}"></i>{n}</td><td class="r">{reais(v)}</td><td class="r">{100*v/x["tot"]:.0f}%</td></tr>' for i, n, v in comp if v > 0)
        mxu = max(x["mes"].values())
        mini = "".join(f'<i style="height:{max(3,100*x["mes"].get(m,0)/mxu):.0f}%" data-tip="{MESES_C[int(m[5:])-1]}: {reais(x["mes"].get(m,0))}"></i>' for m in meses)
        forn = []
        for f, v in x["forn"]:
            if f == "PF":
                nomef = "Pessoas físicas (nomes não exibidos)"
            else:
                nm, doc = f.rsplit("|", 1)
                nomef = FORN_NOMES.get(doc, nm.title() if nm.isupper() else nm)
            forn.append(f"<li><span>{e(nomef)}</span><b>{mi(v)}</b></li>")
        npag = f"{x['n']:,}".replace(",", ".")
        cards.append(f"""<article class="card-sec" id="s-{slug(u)}">
<div class="cab-card"><h3>{e(nome_unidade(u))}</h3><div class="pessoa">{pessoa}</div></div>
<div class="nums"><div><b>{mi(x['tot'])}</b><span>pagos em {ano} ({100*x['tot']/total:.1f}% da Prefeitura)</span></div>
<div><b>{mi(x['tot']/len(meses))}</b><span>por mês, em média</span></div></div>
<div class="mini" aria-label="Pago por mês">{mini}</div><div class="mini-leg"><span>{MESES_C[int(meses[0][5:])-1]}</span><span>{MESES_C[int(meses[-1][5:])-1]}</span></div>
<div class="subt">Para onde vai</div><div class="pilha-sec">{pilha}</div>
<details><summary>Ver valores</summary><table class="t-comp">{tabela}</table></details>
<div class="subt">Quem mais recebeu</div><ol class="forn">{''.join(forn[:6])}</ol>
<p class="small muted" style="margin:0">{npag} pagamentos{link}</p></article>""")
    bate = [k for k, v in conf.items() if v.get("status") == "bate"]
    dif = [k for k, v in conf.items() if v.get("status") == "diferente"]
    falta = [k for k, v in conf.items() if v.get("status") != "bate" and v.get("status") != "diferente"]
    nm = lambda ks: ", ".join(MESES_C[int(k[5:])-1] for k in sorted(ks))
    conferencia = (f"Conferimos o total pago de cada mês com os dados que a Prefeitura manda ao Tribunal de Contas do Estado (TCE-SP): "
                   f"{'<b>bate centavo por centavo</b> em ' + nm(bate) if bate else ''}"
                   f"{'; <b>diferente</b> em ' + nm(dif) if dif else ''}"
                   f"{'. O TCE ainda não publicou ' + nm(falta) if falta else ''}.") if conf else ""
    gasto_pessoal = sum(d["grupos"][u].get("pessoal", 0) for u in d["grupos"])
    corpo = f"""<section class="cab-lista"><span class="eyebrow" style="color:var(--accent)">Raio-X da Prefeitura</span>
<h1>Para onde vai o dinheiro da Prefeitura</h1>
<p>Tudo o que a Prefeitura de Itanhaém pagou em {ano}, secretaria por secretaria, com o nome de quem comanda cada uma. Dados oficiais do <a href="{e(d['fonte'])}" target="_blank" rel="noopener">Portal de Dados Abertos da Prefeitura</a>, atualizados em {data_br(d['coletado_em'])}.</p></section>
<div class="tiles-p">
<div><b>{mi(total)}</b><span>pagos em {ano} até {d['filtro']['emissao_ate'][:5]}</span></div>
<div><b>{mi(total/len(meses))}</b><span>por mês, em média</span></div>
<div><b>{100*gasto_pessoal/total:.0f}%</b><span>vai para salários e encargos dos servidores</span></div>
<div><b>{100*maior[1]['tot']/total:.0f}%</b><span>fica com {e(nome_unidade(maior[0]))}, a maior secretaria</span></div>
</div>
<section class="graf"><h2>Quanto foi pago em cada mês</h2>
<div class="colunas" role="img" aria-label="Total pago por mês em {ano}">{barras_mes}</div>
<p class="small muted">Pela data do pagamento. Janeiro é baixo porque os pagamentos de despesas do ano anterior não entram nesta conta.</p></section>
<section class="graf"><h2>Quanto cada secretaria recebeu em {ano}</h2><ol class="ranking">{ranking}</ol></section>
<section class="graf"><h2>Secretaria por secretaria</h2>
<p class="muted" style="margin:0 0 10px">Toque numa barra para ver o valor.</p><div class="legenda-p">{legenda}</div>
<div class="grade-sec">{''.join(cards)}</div></section>
<section class="prose-p"><h2>Como funciona</h2>
<p>Usamos a consulta <b>Despesas Orçamentárias, despesa paga</b> do portal oficial da Prefeitura: cada pagamento de {ano}, com data, secretaria, tipo de gasto e quem recebeu. A soma ({reais(total)}) é igual ao total que o próprio portal mostra. São {d['linhas']:,} pagamentos.</p>
<p>{conferencia}</p>
<p><b>"Folha de pagamento dos servidores"</b> aparece quando a Prefeitura paga a si mesma para depois creditar os salários: é assim que o sistema registra a folha. <b>Pessoas físicas</b> que receberam pagamentos (prestadores, auxílios) não têm o nome exibido aqui.</p>
<p>Entram só os pagamentos de despesas criadas em {ano}. Contas de anos anteriores pagas agora ("restos a pagar") ficam de fora. Os secretários são os que aparecem nas páginas oficiais da Prefeitura; quando a página não informa, dizemos isso.</p>
</section>""".replace(f"{d['linhas']:,} pag", f"{d['linhas']:,}".replace(",", ".") + " pag")
    return pagina(f"Raio-X da Prefeitura | {NOME}", corpo, "/prefeitura/",
                  f"Quanto cada secretaria da Prefeitura de Itanhaém gastou em {ano} e quem comanda cada uma.", ativo="/prefeitura/")

def home(itens):
    nots = [m for m in itens if m["pasta"] == "noticias"]
    destaque, lateral, resto = nots[0], nots[1:5], nots[5:17]
    c = resumo_camara()
    fmt = lambda n: f"{n:,.0f}".replace(",", ".")
    camara = ""
    if c:
        camara = f"""<a class="bloco-fiscal camara" href="/camara/">
  <span class="eyebrow">Raio-X da Câmara</span><h2>O que cada vereador faz, quanto ganha e quem falta</h2>
  <div class="numeros"><div><b>{fmt(c['props'])}</b><span>propostas dos vereadores desde 2025</span></div>
  <div><b>R$ {fmt(c['salario'])}</b><span>salário de cada um dos {c['cadeiras']} vereadores</span></div>
  <div><b>{c['lic']}</b><span>licitações da Câmara desde 2025</span></div></div>
  <span class="ir">Abrir o Raio-X da Câmara →</span></a>"""
    pd = os.path.join(RAIZ, "dados", "prefeitura_despesas.json")
    nums_pref = '<p>Gastos pagos por secretaria, mês a mês, com dados oficiais do portal da Prefeitura e do Tribunal de Contas.</p>'
    if os.path.exists(pd):
        dp = json.load(open(pd, encoding="utf-8"))
        top = max(dp["unidades"].items(), key=lambda kv: kv[1]["tot"])
        nums_pref = f"""<div class="numeros"><div><b>{mi(dp['total'])}</b><span>pagos pela Prefeitura em {dp['exercicio']}</span></div>
  <div><b>{len(dp['unidades'])}</b><span>secretarias e órgãos, cada um com seu secretário</span></div>
  <div><b>{100*top[1]['tot']/dp['total']:.0f}%</b><span>vai para {e(nome_unidade(top[0]))}</span></div></div>"""
    prefeitura = f"""<a class="bloco-fiscal prefeitura" href="/prefeitura/">
  <span class="eyebrow">Raio-X da Prefeitura</span><h2>Quanto cada secretaria gasta e quem comanda cada uma</h2>
  {nums_pref}
  <span class="ir">Abrir o Raio-X da Prefeitura →</span></a>"""
    cats = sorted({(m["cat"], m["cat_slug"]) for m in nots})
    chips = "".join(f'<a class="chip" href="/noticias/{s}">{e(n)}</a>' for n, s in cats)
    outros = [m for m in itens if m["pasta"] in ("edicoes", "podcasts", "videos")][:4]
    corpo = f"""<h1 class="sr">{NOME}: notícias e fiscalização de Itanhaém</h1>
<section class="manchetes">{cartao(destaque, grande=True)}<div class="lateral">{''.join(cartao(m) for m in lateral)}</div></section>
<section class="fiscal">{camara}{prefeitura}</section>
<section><div class="cab-secao"><h2>Últimas notícias</h2><a href="/noticias">Ver todas →</a></div>
<div class="chips">{chips}</div>
<div class="grade">{''.join(cartao(m) for m in resto)}</div></section>
{f'<section><div class="cab-secao"><h2>Documentos, vídeos e podcasts</h2></div><div class="grade">{"".join(cartao(m) for m in outros)}</div></section>' if outros else ''}"""
    return pagina(f"{NOME} | Notícias e fiscalização de Itanhaém-SP", corpo, "/index",
                  "Notícias de Itanhaém e o Raio-X da Câmara e da Prefeitura, com dados oficiais.", destaque.get("capa", ""), "/")

def rss(itens):
    its = "".join(f"""<item><title>{e(m['titulo'])}</title><link>{URL}{m['url']}</link><guid>{URL}{m['url']}</guid>
<pubDate>{dt.datetime.fromisoformat(m['data']).strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate><description>{e(m.get('subtitulo') or m.get('resumo') or '')}</description></item>"""
                  for m in itens if m["pasta"] == "noticias")
    return f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{NOME}</title><link>{URL}/</link>
<description>Notícias e fiscalização de Itanhaém-SP</description><language>pt-BR</language>{its}</channel></rss>"""

def sitemap(caminhos):
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + \
        "".join(f"<url><loc>{URL}{c}</loc></url>" for c in caminhos) + "</urlset>"

def gravar(rel, txt):
    p = os.path.join(SITE, *rel.strip("/").split("/"))
    os.makedirs(longo(os.path.dirname(p)), exist_ok=True)
    with open(longo(p), "w", encoding="utf-8") as f:
        f.write(txt)

def main():
    itens = carregar()
    caminhos = ["/", "/camara/", "/prefeitura/", "/noticias"]
    for m in itens:
        gravar(m["url"] + ".html", pagina_item(m, itens)); caminhos.append(m["url"])
    nots = [m for m in itens if m["pasta"] == "noticias"]
    cats = sorted({(m["cat"], m["cat_slug"]) for m in nots})
    chips = '<div class="chips">' + "".join(f'<a class="chip" href="/noticias/{s}">{e(n)}</a>' for n, s in cats) + "</div>"
    gravar("noticias.html", pagina_lista("Notícias", f"Todas as {len(nots)} notícias, da mais recente para a mais antiga.", nots, "/noticias", "/noticias", chips))
    for n, s in cats:
        lst = [m for m in nots if m["cat_slug"] == s]
        gravar(f"noticias/{s}.html", pagina_lista(n, f"{len(lst)} notícias.", lst, f"/noticias/{s}", "/noticias", chips)); caminhos.append(f"/noticias/{s}")
    for pasta, (rota, um, lista, pag) in TIPOS.items():
        if pasta == "noticias":
            continue
        lst = [m for m in itens if m["pasta"] == pasta]
        gravar(f"{pag}.html", pagina_lista(lista, "", lst, f"/{pag}", f"/{pag}")); caminhos.append(f"/{pag}")
    gravar("index.html", home(itens))
    pref = pagina_prefeitura()
    if pref:
        gravar("prefeitura/index.html", pref)
    else:  # sem dados da Prefeitura ainda
        gravar("prefeitura/index.html", pagina(f"Raio-X da Prefeitura | {NOME}", """<section class="cab-lista"><span class="eyebrow" style="color:var(--accent)">Em construção</span>
<h1>Raio-X da Prefeitura</h1><p>Em breve: quanto cada secretaria da Prefeitura de Itanhaém gasta por mês, quanto já gastou no ano e quem é o secretário de cada pasta, com dados oficiais.</p>
<p>Enquanto isso, veja o <a href="/camara/">Raio-X da Câmara</a>.</p></section>""", "/prefeitura/", ativo="/prefeitura/"))
    gravar("404.html", pagina(f"Página não encontrada | {NOME}", '<section class="cab-lista"><h1>Página não encontrada</h1><p>O endereço pode ter mudado. <a href="/noticias">Veja todas as notícias</a> ou volte para a <a href="/">página inicial</a>.</p></section>', "/404"))
    gravar("rss.xml", rss(itens)); gravar("sitemap.xml", sitemap(caminhos))
    gravar("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n")
    print(f"site gerado: {len(itens)} publicações, {len(cats)} categorias, {len(caminhos)} páginas no sitemap")

if __name__ == "__main__":
    main()
