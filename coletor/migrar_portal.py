"""Copia as notícias do portal antigo (transparenciaitanhaem.com.br) para arquivos do site novo.

Cada notícia vira conteudo/noticias/<endereço>.md (cabeçalho com título, data, categoria...
e o texto em HTML). Fotos e vídeos enviados ao portal (pasta /uploads/) são baixados para
site/uploads/ no MESMO caminho, para os endereços antigos continuarem valendo.

Uso: python migrar_portal.py   (roda uma vez, antes de desligar o portal antigo)
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request

BASE = "https://www.transparenciaitanhaem.com.br"
UA = "Mozilla/5.0 (migracao do proprio portal)"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_MD = os.path.join(RAIZ, "conteudo", "noticias")
DEST_UP = os.path.join(RAIZ, "site")

def longo(p):
    """No Windows, caminhos com mais de 260 letras precisam do prefixo \\\\?\\."""
    p = os.path.abspath(p)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p

def baixar(url, binario=False):
    for t in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = r.read()
            time.sleep(0.6)
            return d if binario else d.decode("utf-8", "replace")
        except Exception as e:
            print("  erro", url, e, file=sys.stderr); time.sleep(3 * (t + 1))
    return None

def bloco_div(s, ini):
    """Devolve o HTML do <div> que começa em s[ini], com os <div> internos equilibrados."""
    nivel, i = 0, ini
    for m in re.finditer(r"<(/?)div\b[^>]*>", s[ini:]):
        nivel += -1 if m.group(1) else 1
        if nivel == 0:
            return s[ini:ini + m.end()]
    return s[ini:]

def remover_div(s, padrao):
    while True:
        m = re.search(padrao, s)
        if not m:
            return s
        b = bloco_div(s, m.start())
        s = s[:m.start()] + s[m.start() + len(b):]

def extras_corpo(c):
    """Separa créditos e tags (que o portal antigo põe no fim do texto)."""
    fonte = re.search(r"<div class='post-credtis'>.*?</span>(.*?)</div>", c, re.S)
    tags = [html.unescape(t).strip() for t in re.findall(r'/tag/[^"]+"[^>]*>(?:<i[^>]*></i>)?\s*([^<]+)</a>', c)]
    corte = c.find("<div class='post-credtis'>")
    if corte < 0:
        corte = c.find("<div class='tags'>")
    if corte >= 0:
        c = c[:corte]
    return c, (html.unescape(fonte.group(1)).strip() if fonte else ""), tags

def limpar_corpo(c):
    c = re.sub(r'^<div id="content"[^>]*>|</div>\s*$', "", c.strip())
    c = remover_div(c, r'<div id="news-player-wrapper"')
    c = remover_div(c, r"<div class=['\"]related-post")
    c = re.sub(r"(?is)<script.*?</script>", "", c)
    c = re.sub(r'\s(style|class|data-mce-[a-z-]+)="[^"]*"', "", c)
    c = re.sub(r"<(strong|b)>\s*</\1>", "", c)
    c = re.sub(r"<p>\s*(&nbsp;)?\s*</p>", "", c)
    c = c.replace(BASE + "/uploads/", "/uploads/")
    return re.sub(r"\n{3,}", "\n\n", c).strip()

def yaml_str(s):
    return json.dumps(s or "", ensure_ascii=False)

PASTA = {"noticia": "noticias", "podcast": "podcasts", "video": "videos", "evento": "eventos",
         "vaga-de-emprego": "vagas", "edicao": "edicoes", "guia": "guia"}

def migrar_noticia(url, midias, tipo="noticia"):
    s = baixar(url)
    if not s:
        return None
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    titulo = html.unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S).group(1))).strip()
    desc = re.search(r'<meta (?:name|property)="(?:og:)?description" content="([^"]*)"', s)
    sub = re.search(r"</h1>\s*<h2>(.*?)</h2>", s, re.S)
    cat = re.search(r'<div class="post-category">\s*<p style="color:\s*([^;]+);\s*background-color:\s*([^;"]+);?">(.*?)</p>', s, re.S)
    pub = re.search(r'"datePublished"\s*:\s*"([^"]+)"', s)
    mod = re.search(r'"dateModified"\s*:\s*"([^"]+)"', s)
    autor = re.search(r'<span><i>Por</i>\s*(.*?)</span>', s, re.S)
    capa = re.search(r'<meta property="og:image" content="([^"]+)"', s)
    ini = s.find('<div id="content" class="post-content">')
    bruto, fonte, tags = extras_corpo(bloco_div(s, ini)) if ini >= 0 else ("", "", [])
    corpo = limpar_corpo(bruto) if ini >= 0 else ""
    if tipo in ("video", "podcast"):
        players = [html.unescape(u) for u in re.findall(r'<iframe[^>]*src="([^"]+)"', s)
                   if "youtube.com/embed" in u or "soundcloud.com/player" in u]
        if players:
            corpo = f'<iframe src="{players[0]}" title="{html.escape(titulo)}" allowfullscreen loading="lazy"></iframe>\n' + corpo
    arquivo = ""
    if tipo == "edicao":
        pdf = re.search(r"(/uploads/files/[^\"' )]+\.pdf)", s)
        arquivo = pdf.group(1) if pdf else ""
        if arquivo:
            midias.add(arquivo)
    if tipo == "guia":
        tel = sorted(set(re.findall(r'href="tel:([^"]+)"', s)))
        zap = sorted(set(re.findall(r'href="(https://(?:api\.whatsapp\.com|wa\.me)/[^"]+)"', s)))
        insta = sorted(set(re.findall(r'href="(https://(?:www\.)?instagram\.com/[^"]+)"', s)) - {"https://www.instagram.com/transparenciaitanhaem_/?hl=en"})
        end = re.search(r'"streetAddress"\s*:\s*"([^"]+)"', s)
        corpo = (f"<p>{html.escape(html.unescape(desc.group(1)))}</p>" if desc else "") + \
            (f"<p><b>Endereço:</b> {html.escape(end.group(1))}</p>" if end else "") + \
            "".join(f'<p><b>Telefone:</b> <a href="tel:{t}">{t}</a></p>' for t in tel[:2]) + \
            "".join(f'<p><a href="{z}">WhatsApp</a></p>' for z in zap[:1]) + \
            "".join(f'<p><a href="{i}">Instagram</a></p>' for i in insta[:1])
    capa_url = capa.group(1) if capa else ""
    for u in re.findall(r'(?:src|href)="(/uploads/[^"]+)"', corpo) + ([capa_url.replace(BASE, "")] if capa_url.startswith(BASE + "/uploads/") else []):
        midias.add(u.split("?")[0])
    meta = {
        "titulo": titulo, "subtitulo": html.unescape(sub.group(1)).strip() if sub else "",
        "categoria": html.unescape(cat.group(3)).strip() if cat else "Geral",
        "cor": cat.group(2).strip() if cat else "", "data": pub.group(1) if pub else "",
        "atualizado": mod.group(1) if mod else "", "autor": html.unescape(autor.group(1)).strip() if autor else "Transparência Itanhaém",
        "capa": capa_url.replace(BASE, "").split("?")[0], "endereco": slug,
        "tipo": tipo, "resumo": html.unescape(desc.group(1)).strip() if desc else "", "arquivo": arquivo,
        "fonte": fonte, "tags": ", ".join(tags),
    }
    pasta = os.path.join(RAIZ, "conteudo", PASTA[tipo])
    os.makedirs(longo(pasta), exist_ok=True)
    with open(longo(os.path.join(pasta, slug + ".md")), "w", encoding="utf-8") as f:
        f.write("---\n" + "".join(f"{k}: {yaml_str(v)}\n" for k, v in meta.items()) + "---\n\n" + corpo + "\n")
    return meta

def main():
    sm = baixar(BASE + "/sitemap.xml")
    urls = [(u, u.split("/")[3]) for u in re.findall(r"<loc>([^<]+)</loc>", sm) if u.split("/")[3] in PASTA]
    print(len(urls), "publicações no sitemap")
    midias, feitas = set(), []
    for u, tipo in urls:
        m = migrar_noticia(u, midias, tipo)
        if m:
            feitas.append(m); print(" ", tipo, m["data"][:10], m["categoria"], "|", m["titulo"][:70])
    total = 0
    for u in sorted(midias):
        if u.lower().endswith(".mp4"):
            continue  # vídeos ficam fora do site (pesados demais); ver README
        destino = longo(os.path.join(DEST_UP, *urllib.parse.unquote(u).lstrip("/").split("/")))
        if os.path.exists(destino):
            total += os.path.getsize(destino); continue
        d = baixar(BASE + u, binario=True)
        if d:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            open(destino, "wb").write(d); total += len(d)
    print(f"ok: {len(feitas)} notícias, {len(midias)} fotos/vídeos, {total/1e6:.1f} MB")

if __name__ == "__main__":
    main()
