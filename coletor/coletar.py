"""Robo de coleta do Radar Itanhaem.

Baixa SOMENTE dados oficiais do portal da Camara Municipal de Itanhaem (SISCAM):
  - vereadores em exercicio
  - proposituras de cada vereador (exportacao CSV oficial)
  - relatorios de presenca (PDF assinado) de cada sessao

Uso:  python coletar.py <pasta_saida> [anos...]
Requer: pdftotext (poppler/xpdf) no PATH.
"""
import csv, io, json, os, re, subprocess, sys, time, html, urllib.request, urllib.parse

BASE = "https://www.itanhaem.sp.leg.br"
UA = "RadarItanhaem/0.1 (projeto civico de transparencia; coleta lenta)"
PAUSA = 1.2  # segundos entre pedidos, para nao pesar no servidor

def get(path, binario=False, tentativas=3):
    url = path if path.startswith("http") else BASE + path
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                dados = r.read()
            time.sleep(PAUSA)
            return dados if binario else dados.decode("utf-8", "replace")
        except Exception as e:
            print("  erro", url, e, file=sys.stderr)
            time.sleep(5 * (t + 1))
    raise RuntimeError("falhou: " + url)

def vereadores_atuais():
    out, pag = [], 1
    while True:
        d = json.loads(get(f"/siscam/Documentos?handler=autor&tipoAutorId=1&todos=true&pagina={pag}&texto="))
        out += [{"id": r["id"], "nome": r["text"]} for r in d["results"] if not r["secondary"]]
        if not d.get("more"):
            return out
        pag += 1

def baixar_fotos(vers, pasta):
    """Fotos oficiais da pagina de vereadores da Camara. Cada foto vem antes do link 'Detalhes' do mesmo cartao."""
    s = get("/vereadores?tab=vereadores")
    pares = re.findall(r'src="(/Vereadores\?id=\d+&amp;handler=ImagemVereadores)".*?href="/Vereadores/Details\?id=(\d+)"', s, re.S)
    os.makedirs(pasta, exist_ok=True)
    ids = {v["id"] for v in vers}
    for src, vid in pares:
        vid = int(vid)
        if vid not in ids or any(v.get("foto") for v in vers if v["id"] == vid):
            continue
        img = get(html.unescape(src), binario=True)
        ext = ".png" if img[:4] == b"\x89PNG" else ".webp" if img[8:12] == b"WEBP" else ".jpg"
        nome = f"{vid}.jpg"
        destino = os.path.join(pasta, nome)
        try:  # reduz para 480px de largura (fotos originais chegam a 3 MB)
            from PIL import Image
            im = Image.open(io.BytesIO(img)).convert("RGB")
            im.thumbnail((480, 480 * im.height // im.width + 1))
            im.save(destino, "JPEG", quality=82, optimize=True)
        except ImportError:
            nome = f"{vid}{ext}"; destino = os.path.join(pasta, nome)
            open(destino, "wb").write(img)
        for v in vers:
            if v["id"] == vid:
                v["foto"] = "fotos/" + nome
    print("fotos:", sum(1 for v in vers if v.get("foto")), "de", len(vers))

def mesa_diretora(vers):
    """Cargos da Mesa Diretora: o cargo aparece antes do link 'Detalhes' de cada vereador."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", get("/vereadores?tab=mesa"))
    ini = max(0, s.find("/Vereadores/Details?id=") - 1500)
    for m in re.finditer(r"Vereadores/Details\?id=(\d+)", s[ini:]):
        antes = html.unescape(re.sub(r"<[^>]+>", "|", s[ini:][max(0, m.start() - 600):m.start()]))
        cargos = re.findall(r"(?i)(vice-presidente|presidente|\d\S? secret[aá]rio)", antes)
        if not cargos:
            continue
        cargo = cargos[-1].lower().replace("secretario", "secretário")
        cargo = cargo[0].upper() + cargo[1:]
        cargo = re.sub(r"(\d\S?) secretário", lambda x: x.group(1).replace("ª", "º").replace("°", "º") + " Secretário", cargo)
        for v in vers:
            if v["id"] == int(m.group(1)) and "cargo" not in v:
                v["cargo"] = cargo + " da Câmara"
    print("mesa:", {v["apelido"]: v.get("cargo") for v in vers if v.get("cargo")})

def apelido(nome):
    m = re.findall(r"\(([^)]+)\)", nome)
    m = [x for x in m if x.upper() != "VEREADOR"]
    return (m[-1] if m else nome).title()

def proposituras(autor_id, ano):
    q = urllib.parse.urlencode({"Pesquisa": "Avancada", "GrupoId": 7, "TipoAutorId": 1, "AutorId": autor_id,
                                "TipoIniciativaId": 1, "Ano": ano, "Ordenacao": 4, "Export": "Csv"})
    txt = get("/siscam/Documentos?" + q).lstrip("\ufeff")
    rows = []
    for r in csv.DictReader(io.StringIO(txt)):
        mes, dia, resto = (r["Data"] or "//").split("/", 2)
        rows.append({"id": int(r["Id"]), "tipo": r["Tipo"], "num": r["Numero"], "ano": int(r["Ano"]),
                     "data": f"{resto[:4]}-{mes}-{dia}" if resto else "",
                     "ementa": re.sub(r"^[\s\"“”]+|[\s\"“”]+$", "", r["Ementa"] or "")})
    return rows

def sessoes(ano):
    q = urllib.parse.urlencode({"Pesquisa": "Avancada", "TipoId": 1, "Ano": ano, "ItemsPerPage": 100, "Ordenacao": 4})
    s = get("/siscam/Reunioes?" + q)
    total = int(re.search(r"([\d\.]+) registros", s).group(1).replace(".", ""))
    itens = re.findall(r'Reunioes/Details\?id=(\d+)"[^>]*>\s*([^<]+)', s)
    vistos, out = set(), []
    for i, t in itens:
        if i in vistos: continue
        vistos.add(i); out.append({"id": int(i), "titulo": html.unescape(t).strip()})
    if len(out) != total:
        raise RuntimeError(f"sessoes {ano}: lista com {len(out)} mas portal diz {total}")
    return out

def ler_presenca(pdf_bytes, tmp):
    with open(tmp, "wb") as f: f.write(pdf_bytes)
    txt = subprocess.run(["pdftotext", "-f", "1", "-l", "1", "-raw", "-enc", "UTF-8", tmp, "-"],
                         capture_output=True).stdout.decode("utf-8", "replace").replace("\r", "")
    data = re.search(r"Data (\d\d/\d\d/\d{4})", txt)
    regs = re.findall(r"^(\S+(?: \S+)*?) (PRESENTE|Ausente|AUSENTE|Justificad\w*|JUSTIFICAD\w*|Licen\w*|LICEN\w*)\n\d+\n(.+?)(?: (\d\d:\d\d:\d\d))?\n(\d+)$",
                      txt, re.M)
    hab = re.search(r"Habilitados: (\d+)", txt)
    return {"data": data.group(1) if data else None,
            "habilitados": int(hab.group(1)) if hab else None,
            "registros": [{"id": int(i), "partido": p, "status": st.upper(), "nome": n.strip()} for p, st, n, h, i in regs]}

def main():
    saida = sys.argv[1]; anos = [int(a) for a in sys.argv[2:]] or [2025, 2026]
    os.makedirs(saida, exist_ok=True); tmp = os.path.join(saida, "_tmp.pdf")
    vers = vereadores_atuais()
    for v in vers:
        v["apelido"] = apelido(v["nome"])
    print(len(vers), "vereadores")
    baixar_fotos(vers, os.path.join(saida, "fotos"))
    mesa_diretora(vers)
    for v in vers:
        v["props"] = []
        for a in anos:
            v["props"] += proposituras(v["id"], a)
        print(" ", v["apelido"], len(v["props"]), "proposituras")
    ses_out = []
    for a in anos:
        for s in sessoes(a):
            if "Secreta" in s["titulo"]:
                continue
            pag = get(f"/Siscam/Reunioes/Details?id={s['id']}")
            m = re.search(r"Data:\s*</[^>]+>\s*(?:<[^>]+>\s*)*(\d\d/\d\d/\d{4})", pag)
            s["data_pagina"] = m.group(1) if m else None
            s["chamadas"] = []
            for tit, arq in re.findall(r'title="(PRESEN[^"]*)"[^>]*href="/Siscam/Documentos\?handler=Arquivo&amp;id=(\d+)"', pag):
                p = ler_presenca(get(f"/Siscam/Documentos?handler=Arquivo&id={arq}", binario=True), tmp)
                p["arquivo"] = int(arq); p["titulo"] = html.unescape(tit)
                s["chamadas"].append(p)
            ses_out.append(s)
            print(" ", s["titulo"], "chamadas:", len(s["chamadas"]), [len(c["registros"]) for c in s["chamadas"]])
    if os.path.exists(tmp): os.remove(tmp)
    json.dump({"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "anos": anos, "vereadores": vers, "sessoes": ses_out},
              open(os.path.join(saida, "dados.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("ok")

if __name__ == "__main__":
    main()
