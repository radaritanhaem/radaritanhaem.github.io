"""Passo 5: confere a presenca de cada relatorio com a ata da mesma sessao.

- Le o titulo real da sessao dentro do PDF de presenca (o PDF fica anexado na sessao seguinte).
- Baixa a ata anexada junto e procura os vereadores que a ata marca como AUSENTE.
- Grava o titulo real em dados.json e um relatorio em verificacao.json.
Uso: python verificar.py <dados.json> <verificacao.json>
"""
import json, re, subprocess, sys, html, os, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar import get

def sa(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper()

def texto_pdf(b, tmp, raw=True, paginas=None):
    open(tmp, "wb").write(b)
    cmd = ["pdftotext", "-enc", "UTF-8"] + (["-raw"] if raw else []) + (["-f", "1", "-l", str(paginas)] if paginas else []) + [tmp, "-"]
    return subprocess.run(cmd, capture_output=True).stdout.decode("utf-8", "replace").replace("\r", "")

def main():
    dados = json.load(open(sys.argv[1], encoding="utf-8")); tmp = "_v.pdf"
    nomes = {v["id"]: sa(re.sub(r"\(.*", "", v["nome"])).split() for v in dados["vereadores"]}
    rel = []
    for s in dados["sessoes"]:
        if not s["chamadas"]:
            continue
        pdf = texto_pdf(get(f"/Siscam/Documentos?handler=Arquivo&id={s['chamadas'][0]['arquivo']}", binario=True), tmp, paginas=1)
        m = re.search(r"(\d+\S* Sess\S+ [^\n]+? de \d{4})", pdf)
        s["sessao_real"] = m.group(1).strip() if m else None
        pag = get(f"/Siscam/Reunioes/Details?id={s['id']}")
        atas = re.findall(r'title="(ATA[^"]*)"[^>]*href="/Siscam/Documentos\?handler=Arquivo&amp;id=(\d+)"', pag, re.I)
        atas = [(html.unescape(t), i) for t, i in atas if "PRESEN" not in html.unescape(t).upper()]
        aus_rel = sorted({r["id"] for c in s["chamadas"] for r in c["registros"]} -
                         {r["id"] for c in s["chamadas"] for r in c["registros"] if r["status"] == "PRESENTE"})
        item = {"sessao": s["sessao_real"], "pagina": s["id"], "ausentes_relatorio": aus_rel, "ata": None}
        if atas:
            ata = sa(texto_pdf(get(f"/Siscam/Documentos?handler=Arquivo&id={atas[0][1]}", binario=True), tmp, raw=False))
            ata = re.sub(r"\s+", " ", ata)
            trechos = re.findall(r"\(([^()]*AUSENTE[^()]*)\)", ata)
            aus_ata = sorted({vid for vid, partes in nomes.items() for t in trechos
                              if sum(1 for p in partes if len(p) > 3 and p in t) >= 2})
            item.update({"ata": atas[0][0], "trechos_ata": trechos, "ausentes_ata": aus_ata,
                         "bate": aus_ata == aus_rel})
        rel.append(item)
        print(item["sessao"], "| relatorio:", aus_rel, "| ata:", item.get("ausentes_ata"), "| OK" if item.get("bate") else "| DIFERENTE")
    if os.path.exists(tmp): os.remove(tmp)
    json.dump(dados, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(rel, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in rel if r.get("bate")); print(f"bate em {ok} de {len(rel)} sessoes")

if __name__ == "__main__":
    main()
