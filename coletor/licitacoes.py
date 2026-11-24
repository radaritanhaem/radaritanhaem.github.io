"""Licitações e contratações da Câmara de Itanhaém.

Fontes oficiais:
  - Página de licitações da Câmara: https://www.itanhaem.sp.leg.br/licitacao
  - PNCP (Portal Nacional de Contratações Públicas), onde a Câmara é obrigada a publicar
    valor estimado, valor homologado e empresa vencedora de cada item.

Uso: python licitacoes.py <saida.json> [ano_minimo]
"""
import html, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coletar import get

CNPJ = "54353586000105"
PNCP = "https://pncp.gov.br/api"

def limpa(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()

def campo(bloco, nome):
    m = re.search(nome + r":\s*</[^>]+>\s*(?:<[^>]+>\s*)*([^<]+)", bloco)
    return limpa(m.group(1)) if m else ""

def pagina(n):
    s = get(f"/Licitacao?CurrentPage={n}")
    tot = re.search(r"([\d\.]+) registros", s)
    partes = re.split(r'(?=<div class="licitacao-header)', s)[1:]
    itens = []
    for b in partes:
        idm = re.search(r'collapse-licitacao-(\d+)', b)
        if not idm:
            continue
        data = re.search(r'licitacao-date[^>]*>\s*(\d\d/\d\d/\d{4})', b)
        titulo = re.search(r'licitacao-title[^>]*>(.*?)</div>', b, re.S)
        pncp = re.search(r'href="(https://pncp\.gov\.br/app/editais/(\d+)/(\d{4})/(\d+))"', b)
        # objeto: primeiro paragrafo de texto depois do botao "imprimir PDF"
        apos = b.split("imprimir PDF", 1)[-1]
        objeto = limpa(apos.split("Modalidade:", 1)[0])
        anexos = [(limpa(t), html.unescape(h)) for h, t in
                  re.findall(r'href="(/Licitacao\?id=\d+&amp;handler=Imagem)"[^>]*>(.*?)</a>', b, re.S)]
        itens.append({
            "id": int(idm.group(1)), "data": data.group(1) if data else "",
            "titulo": limpa(titulo.group(1)) if titulo else "",
            "objeto": objeto, "modalidade": campo(b, "Modalidade"), "julgamento": campo(b, "Julgamento"),
            "etapa": campo(b, "Etapa"), "abertura": campo(b, "Abertura"), "processo": campo(b, "Processo"),
            "pncp": pncp.group(1) if pncp else None,
            "pncp_ano": int(pncp.group(3)) if pncp else None, "pncp_seq": int(pncp.group(4)) if pncp else None,
            "anexos": [{"nome": t, "url": h} for t, h in anexos],
        })
    return itens, int(tot.group(1).replace(".", "")) if tot else None

def pncp_json(path):
    try:
        return json.loads(get(PNCP + path))
    except Exception as e:
        print("  pncp sem resposta:", path, e, file=sys.stderr)
        return None

def detalhes_pncp(ano, seq):
    c = pncp_json(f"/consulta/v1/orgaos/{CNPJ}/compras/{ano}/{seq}")
    if not c:
        return None
    out = {"estimado": c.get("valorTotalEstimado"), "homologado": c.get("valorTotalHomologado"),
           "situacao": c.get("situacaoCompraNome"), "modalidade_pncp": c.get("modalidadeNome"),
           "amparo": (c.get("amparoLegal") or {}).get("nome"), "vencedores": []}
    itens = pncp_json(f"/pncp/v1/orgaos/{CNPJ}/compras/{ano}/{seq}/itens?pagina=1&tamanhoPagina=200") or []
    venc = {}
    for it in itens[:80]:
        if not it.get("temResultado"):
            continue
        for r in pncp_json(f"/pncp/v1/orgaos/{CNPJ}/compras/{ano}/{seq}/itens/{it['numeroItem']}/resultados") or []:
            if r.get("situacaoCompraItemResultadoNome") == "Cancelado":
                continue
            pj = r.get("tipoPessoa") == "PJ"
            nome = r.get("nomeRazaoSocialFornecedor") if pj else "Pessoa física (nome não exibido)"
            chave = r.get("niFornecedor") if pj else "PF"
            v = venc.setdefault(chave, {"nome": nome, "cnpj": r.get("niFornecedor") if pj else None, "valor": 0.0, "itens": 0})
            v["valor"] += float(r.get("valorTotalHomologado") or 0)
            v["itens"] += 1
    out["vencedores"] = sorted(venc.values(), key=lambda v: -v["valor"])
    if out["homologado"] in (None, 0) and venc:
        out["homologado_soma_itens"] = round(sum(v["valor"] for v in venc.values()), 2)
    return out

def main():
    saida = sys.argv[1]; ano_min = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    todas, n, total = [], 1, None
    while True:
        itens, tot = pagina(n)
        total = total or tot
        if not itens:
            break
        todas += itens
        if total and len(todas) >= total:
            break
        n += 1
    if total and len(todas) != total:
        raise RuntimeError(f"licitacoes: li {len(todas)} mas o portal diz {total}")
    print(len(todas), "licitacoes no portal")
    sel = [l for l in todas if l["data"] and int(l["data"][-4:]) >= ano_min]
    for l in sel:
        if l["pncp"]:
            l["pncp_dados"] = detalhes_pncp(l["pncp_ano"], l["pncp_seq"])
        print(" ", l["data"], l["titulo"][:60], "|", (l.get("pncp_dados") or {}).get("homologado"))
    json.dump({"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "total_portal": total, "ano_min": ano_min,
               "licitacoes": sel}, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok", len(sel))

if __name__ == "__main__":
    main()
