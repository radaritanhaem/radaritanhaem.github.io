"""Alertas do Tribunal de Contas do Estado (TCE-SP) para a Prefeitura, a Câmara e o ITAPREV de Itanhaém.

Duas fontes oficiais e públicas:
  1. Comunicados SDG "ALERTAS de que trata o parágrafo 1º do artigo 59 da LRF" (um a cada bimestre),
     com a lista de Prefeituras, Câmaras e entidades (ex.: institutos de previdência) alertadas.
     O PDF é lido com `pdftotext -raw`; cada linha com "Itanhaém" é classificada pela seção do comunicado.
     Se a linha não cair numa seção conhecida, ela NÃO vai para o site (fica em "a_conferir" no registro).
  2. Painel Visor do TCE-SP: quantos alertas a Prefeitura recebeu no ano, por assunto.

Nomes de prefeito / presidente que aparecem nos comunicados não são guardados.

Uso: python coletor/tce_alertas.py dados/tce_alertas.json [ano]
"""
import html, http.cookiejar, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request

TCE = "https://www.tce.sp.gov.br"
VISOR = "https://painel.tce.sp.gov.br/pentaho"
VISOR_PAGINA = "https://www.tce.sp.gov.br/visor"
IBGE = 3522109
UA = "Mozilla/5.0 (robo do Transparencia Itanhaem; consulta lenta)"
ASSUNTOS = ["LRF", "ENSINO", "SAÚDE", "CUMPRIMENTO DAS INSTRUÇÕES DO TCE", "PLANEJAMENTO ORÇAMENTÁRIO"]

INCISOS = {  # LRF, art. 59, § 1º (em linguagem simples)
    "I": "a arrecadação pode não ser suficiente para cumprir as metas fiscais do ano",
    "II": "o gasto com pessoal passou de 90% do limite da Lei de Responsabilidade Fiscal",
    "III": "a dívida, as operações de crédito ou as garantias passaram de 90% do limite",
    "IV": "o gasto com inativos e pensionistas passou do limite",
    "V": "há fatos que comprometem os custos ou resultados dos programas, ou indícios de irregularidade na gestão do orçamento",
}

op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def get(url, dados=None, tentativas=3):
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, data=dados, headers={"User-Agent": UA, **({"Content-Type": "application/x-www-form-urlencoded"} if dados else {})})
            with op.open(req, timeout=120) as r:
                b = r.read()
            time.sleep(1)
            return b
        except Exception as e:
            print("  erro", url[:90], e, file=sys.stderr); time.sleep(6 * (t + 1))
    raise RuntimeError("falhou: " + url)

# ---------- comunicados ----------
def listar_comunicados(ano):
    vistos, out = set(), []
    for p in range(4):
        h = get(f"{TCE}/legislacao?termo=ALERTAS%20artigo%2059&f%5B0%5D=tipo%3A18&page={p}").decode("utf-8", "replace")
        for slug in re.findall(r'href="(/legislacao/comunicado/alertas-trata-paragrafo-1o-artigo-59[^"]*)"', h):
            if slug in vistos:
                continue
            vistos.add(slug)
            pg = get(TCE + slug).decode("utf-8", "replace")
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", pg)))
            data = re.search(r"Data de Publicação:\s*(\d\d)/(\d\d)/(\d{4})", txt)
            num = re.search(r"COMUNICADO SDG N[ºo°]\s*(\d+)/(\d{4})", txt, re.I)
            rel = re.search(r"relativos? ao (.{5,140}?) d[oa]s? Câmaras", txt)
            pdfs = [u for u in re.findall(r'href="([^"]+\.pdf)"', pg) if "DOE" not in u and "Publica" not in u]
            if not (data and pdfs) or data.group(3) != str(ano):
                continue
            out.append({"numero": f"{num.group(1)}/{num.group(2)}" if num else "", "data": f"{data.group(3)}-{data.group(2)}-{data.group(1)}",
                        "relativo": rel.group(1).strip() if rel else "", "pagina": TCE + slug, "pdf": urllib.parse.urljoin(TCE, pdfs[0])})
    return sorted(out, key=lambda c: c["data"])

SECOES = [  # (regex do título, chave)
    (r"inciso II da LRF", "pessoal"),
    (r"Incisos? I\b", "incisos"),
    (r"MUNIC[IÍ]PIOS QUE DEIXARAM DE ENVIAR", "balancete_prefeitura"),
    (r"^\s*1\.\s*C[AÂ]MARAS MUNICIPAIS", "balancete_camara"),
    (r"^\s*2\.\s*ENTIDADES MUNICIPAIS", "balancete_indireta"),
    (r"C[AÂ]MARAS MUNICIPAIS E ENTIDADES", None),
]

def ler_pdf(caminho_pdf):
    """Devolve as linhas do comunicado que falam de Itanhaém, já classificadas."""
    txt = subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", caminho_pdf, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    secao, periodo, achados = None, "", []
    for l in txt.splitlines():
        m = re.search(r"SISTEMA AUDESP\s*[–-]\s*(.+)", l)
        if m:
            periodo = m.group(1).strip()
        for rx, k in SECOES:
            if re.search(rx, l, re.I):
                secao = k
                break
        if not re.search(r"Itanha[eé]m", l, re.I):
            continue
        a = {"secao": secao, "periodo": periodo}
        if secao == "incisos":
            inc = re.search(r"\b((?:I|II|III|IV|V)(?:\s*,\s*(?:I|II|III|IV|V))*)\s*$", l.strip())
            a["incisos"] = re.split(r"\s*,\s*", inc.group(1)) if inc else []
            a["orgao"] = "prefeitura"
        elif secao == "pessoal":
            pct = re.search(r"(\d{2},\d{2})\s*$", l.strip())
            a.update(orgao="prefeitura", incisos=["II"], percentual=pct.group(1) if pct else "")
        elif secao == "balancete_prefeitura":
            a["orgao"] = "prefeitura"
        elif secao == "balancete_camara":
            a["orgao"] = "camara"
        elif secao == "balancete_indireta":
            a["orgao"] = "itaprev" if re.search(r"PREVID|ITAPREV|IPREV", l, re.I) else "outra"
        ok = a.get("orgao") in ("prefeitura", "camara", "itaprev") and (secao not in ("incisos",) or a.get("incisos"))
        a["conferido"] = bool(ok)
        achados.append(a)
    return achados

def texto_alerta(a):
    if a["secao"] in ("incisos", "pessoal"):
        partes = [f"{INCISOS[i]} (inciso {i})" for i in a.get("incisos", []) if i in INCISOS]
        t = "; ".join(partes)
        if a.get("percentual"):
            t += f". Gasto com pessoal: {a['percentual']}% da receita corrente líquida"
        return t[:1].upper() + t[1:]
    if a["secao"].startswith("balancete"):
        return "Não tinha enviado ao TCE o balancete contábil (a prestação de contas do bimestre) quando o Tribunal fez a análise"
    return ""

# ---------- Visor ----------
def visor(ano):
    get(f"{VISOR}/api/repos/%3Apublic%3AVisor%3Avisor.wcdf/generatedContent?userid=anony&password=zero")
    out, vazio = {}, True
    for a in ASSUNTOS:
        d = urllib.parse.urlencode({"path": "/public/Visor/visor.cda", "dataAccessId": "visorDS", "outputType": "json",
                                    "parampAno": str(ano), "parampEntidade": "PREFEITURA MUNICIPAL", "parampAssunto": a}).encode()
        r = json.loads(get(f"{VISOR}/plugin/cda/api/doQuery", d))
        linha = [x for x in r["resultset"] if x[0] == IBGE]
        out[a] = int(linha[0][3]) if linha else 0
        vazio = vazio and not r.get("resultset")
    if vazio:
        raise RuntimeError("o Visor não devolveu dados de nenhum município (o painel mudou?)")
    return out

def coletar(ano):
    res = {"exercicio": ano, "coletado_em": time.strftime("%Y-%m-%d"), "fonte_comunicados": f"{TCE}/comunicados",
           "fonte_visor": VISOR_PAGINA, "comunicados": [], "a_conferir": []}
    tmp = tempfile.mkdtemp()
    for c in listar_comunicados(ano):
        p = os.path.join(tmp, "c.pdf")
        open(p, "wb").write(get(c["pdf"]))
        for a in ler_pdf(p):
            if a.pop("conferido"):
                c.setdefault("alertas", []).append({**a, "texto": texto_alerta(a)})
            else:
                res["a_conferir"].append({"comunicado": c["numero"], **a})
        res["comunicados"].append(c)
        print(f"  comunicado {c['numero']} ({c['data']}): {len(c.get('alertas', []))} alerta(s) para Itanhaém")
    if not res["comunicados"]:
        raise RuntimeError("nenhum comunicado de alertas encontrado no site do TCE (o site mudou?)")
    try:
        res["visor_prefeitura"] = visor(ano)
    except Exception as e:
        print("  Visor indisponível:", e, file=sys.stderr)
    for x in res["a_conferir"]:
        print("  A CONFERIR (não publicado):", x, file=sys.stderr)
    return res

if __name__ == "__main__":
    ano = int(sys.argv[2]) if len(sys.argv) > 2 else int(time.strftime("%Y"))
    r = coletar(ano)
    json.dump(r, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(c.get("alertas", [])) for c in r["comunicados"])
    print(f"alertas TCE {ano}: {len(r['comunicados'])} comunicados, {n} alerta(s) para Itanhaém, Visor: {r.get('visor_prefeitura')}")
