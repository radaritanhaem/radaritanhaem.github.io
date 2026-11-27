"""Raio-X da Prefeitura de Itanhaém: gasto pago por secretaria + quem é o secretário.

Fontes oficiais:
  - Portal de Dados Abertos da Prefeitura (sistema GCASP): Despesas Orçamentárias, "Despesa paga",
    exportação CSV com cada pagamento (data, fornecedor, secretaria, natureza, valor).
  - Páginas oficiais de cada secretaria em itanhaem.sp.gov.br (nome e formação do secretário).
  - TCE-SP (API de transparência): total pago por mês, usado só para CONFERIR.

Regras: nome de pessoa física que recebeu pagamento NUNCA vai para o site (só empresas, com CNPJ).

Uso:
  python prefeitura.py despesas <saida.json> [ano]     (precisa do Playwright)
  python prefeitura.py secretarios <saida.json>
  python prefeitura.py conferir <despesas.json> <saida.json>
"""
import collections, csv, html, io, json, re, sys, time, unicodedata, urllib.request

UA = "RadarItanhaem/0.1 (projeto civico de transparencia; coleta lenta)"
PORTAL = "https://dadosabertos.itanhaem.sp.gov.br"
PORTAL_PREF = PORTAL
ORGAO = "2"  # 2 = Prefeitura; 3 = ITAPREV (que fica em outro endereço do mesmo sistema)

def usar_itaprev():
    global PORTAL, ORGAO
    PORTAL, ORGAO = "https://transparenciaonline.gcaspp.com", "3"

def entrar(pg):
    """O portal do ITAPREV só abre depois de escolher o órgão no portal da Prefeitura (ele redireciona)."""
    if ORGAO == "2":
        return
    pg.goto(PORTAL_PREF + "/home?Inicio", wait_until="domcontentloaded", timeout=120000)
    pg.wait_for_selector("#vORGAO_MPAGE", timeout=90000); time.sleep(2)
    pg.select_option("#vORGAO_MPAGE", ORGAO)
    pg.wait_for_url("**gcaspp.com/**", timeout=120000); time.sleep(3)
SITE_PREF = "https://www.itanhaem.sp.gov.br"
CNPJ_PREF = "46.578.498/0001-75"

def get(url, tentativas=3, timeout=120):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
                d = r.read()
            time.sleep(1.2)
            return d.decode("utf-8", "replace")
        except Exception as e:
            print("  erro", url, e, file=sys.stderr); time.sleep(8 * (t + 1))
    raise RuntimeError("falhou: " + url)

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()

# ---------------- gasto por secretaria ----------------
def grupo(natureza):
    n = natureza
    if re.match(r"3\.1\.", n): return "pessoal"
    if re.match(r"4\.4\.90\.(51|61)", n): return "obras"
    if re.match(r"4\.4\.", n): return "equipamentos"
    if "SENTEN" in n: return "sentencas"
    if re.match(r"4\.6\.|3\.2\.", n): return "divida"
    if re.match(r"3\.3\.90\.(30|32)", n): return "material"
    if re.match(r"3\.3\.(50|60|67|70|71|80|41|43|45)\.", n): return "repasses"
    if re.match(r"3\.3\.90\.(39|36|37|33|35|40)", n): return "servicos"
    return "outros"

def agregar(texto_csv):
    linhas = list(csv.reader(io.StringIO(texto_csv), delimiter=";"))
    cab = [c.strip() for c in linhas[0]]
    i = {n: cab.index(n) for n in ("Unidade Orçamentária", "Data Pagamento", "CPF / CNPJ", "Fornecedor", "Natureza da Despesa", "Valor Pago")}
    U, meses, total, n = {}, collections.Counter(), 0, 0
    nat_total, forn_nat = collections.Counter(), collections.Counter()
    PJ = {}  # todo CNPJ que recebeu: para achar entidades sem fins lucrativos pelo cadastro da Receita
    for c in linhas[1:]:
        if len(c) != len(cab):
            raise RuntimeError(f"linha com {len(c)} colunas (esperado {len(cab)}): {';'.join(c)[:120]}")
        v = round(float(c[i["Valor Pago"]].strip()) * 100)
        dp = c[i["Data Pagamento"]].strip().zfill(8)
        mes = f"{dp[4:8]}-{dp[2:4]}"
        un = c[i["Unidade Orçamentária"]].strip()
        u = U.setdefault(un, {"tot": 0, "n": 0, "mes": collections.Counter(), "forn": collections.Counter(), "nat": collections.Counter(), "grupo": collections.Counter()})
        doc = c[i["CPF / CNPJ"]].strip()
        pj = re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", doc)
        u["forn"][f"{c[i['Fornecedor']].strip()}|{doc}" if pj else "PF"] += v
        nat = c[i["Natureza da Despesa"]].strip()
        u["nat"][nat] += v; u["grupo"][grupo(nat)] += v; nat_total[nat] += v
        if pj:
            forn_nat[f"{c[i['Fornecedor']].strip()}|{doc}|{nat}"] += v
            e = PJ.setdefault(doc, {"nome": c[i["Fornecedor"]].strip(), "tot": 0, "n": 0, "un": collections.Counter(), "nat": collections.Counter(),
                                    "mes": collections.Counter(), "mod": collections.Counter(), "obj": collections.Counter()})
            e["tot"] += v; e["n"] += 1; e["un"][un] += v; e["nat"][nat] += v; e["mes"][mes] += v
            if "Modalidade" in cab: e["mod"][c[cab.index("Modalidade")].strip()] += v
            if "Obj. contratação" in cab and c[cab.index("Obj. contratação")].strip():
                e["obj"][re.sub(r"\s+", " ", c[cab.index("Obj. contratação")].strip())[:200]] += v
        u["tot"] += v; u["n"] += 1; u["mes"][mes] += v; meses[mes] += v; total += v; n += 1
    top = lambda c, k: [[a, b] for a, b in c.most_common(k)]
    return {"linhas": n, "total": total, "meses": dict(meses),
            "unidades": {k: {"tot": u["tot"], "n": u["n"], "mes": dict(u["mes"]), "forn": top(u["forn"], 12), "nat": top(u["nat"], 8)} for k, u in U.items()},
            "grupos": {k: dict(u["grupo"]) for k, u in U.items()},
            "nat": [[a, b] for a, b in nat_total.most_common()], "forn": [[a, b] for a, b in forn_nat.most_common(60)],
            "mes": dict(meses), "un": [[k, u["tot"]] for k, u in sorted(U.items(), key=lambda kv: -kv[1]["tot"])],
            "pj": {k: {"nome": e["nome"], "tot": e["tot"], "n": e["n"], "un": top(e["un"], 5), "nat": top(e["nat"], 5), "mes": dict(e["mes"]),
                         "mod": top(e["mod"], 3), "obj": top(e["obj"], 3)} for k, e in PJ.items()}}

def despesas(ano):
    """Abre o portal no navegador (Playwright), pede todos os pagamentos do ano e baixa o CSV oficial."""
    from playwright.sync_api import sync_playwright
    hoje = time.strftime("%d/%m/%Y") if int(time.strftime("%Y")) == ano else f"31/12/{ano}"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 (robo do Transparencia Itanhaem; coleta lenta)", locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        try:
            return _despesas(pg, ctx, nav, ano, hoje)
        except Exception:
            registrar_falha(pg, "prefeitura" if ORGAO == "2" else "itaprev-despesas")
            raise

def registrar_falha(pg, nome):
    import os
    os.makedirs("dados/registro", exist_ok=True)
    try:
        pg.screenshot(path=f"dados/registro/{nome}.png", full_page=True)
        open(f"dados/registro/{nome}.html", "w", encoding="utf-8").write(pg.content()[:300000])
        print("  falha registrada:", nome, pg.url, file=sys.stderr)
        if "verificação de segurança" in pg.content() or "challenge-platform" in pg.content():
            print("  MOTIVO: o portal mostrou a verificação anti-robô (Cloudflare) e não liberou o acesso automático."
                  " O site continua com os últimos dados bons; colete pelo navegador do app.", file=sys.stderr)
    except Exception as e:
        print("  não consegui registrar a falha:", e, file=sys.stderr)

def _despesas(pg, ctx, nav, ano, hoje):
    if True:
        entrar(pg)
        pg.goto(PORTAL + "/filtros-despesasorcamentarias", wait_until="domcontentloaded", timeout=120000)
        pg.wait_for_selector("#vORGAO_MPAGE", timeout=90000); time.sleep(2)
        if pg.eval_on_selector("#vORGAO_MPAGE", "s => s.value") != ORGAO:
            pg.select_option("#vORGAO_MPAGE", ORGAO); time.sleep(4)
        if pg.eval_on_selector("#vEXERCICIO_MPAGE", "s => s.value") != str(ano):
            pg.select_option("#vEXERCICIO_MPAGE", str(ano)); time.sleep(4)
        pg.evaluate("""async ([ini, fim]) => {
          const sleep = ms => new Promise(r => setTimeout(r, ms));
          for (let k = 0; k < 60 && !document.getElementById('W0012vDATAINICIAL'); k++) await sleep(250);
          for (const [id, v] of [['W0012vDATAINICIAL', ini], ['W0012vDATAFINAL', fim]]) {
            const i = document.getElementById(id); i.focus(); i.value = v;
            i.dispatchEvent(new Event('input', {bubbles: true})); i.dispatchEvent(new Event('change', {bubbles: true})); i.blur(); await sleep(400); }
          const b = document.getElementById('W0012COMBO_UNIDADEORCAMENTARIAContainer_btnGroupDrop');
          if (b) { b.click(); await sleep(800);
            const g = [...b.parentElement.querySelectorAll('a')].find(a => a.innerText.trim() == 'GERAL'); if (g) g.click(); await sleep(1200); }
          const s = document.getElementById('W0012vCONSIDERAR'); s.value = '4'; s.dispatchEvent(new Event('change', {bubbles: true})); await sleep(600);
          document.getElementById('W0012BTNENTER').click();
        }""", [f"01/01/{ano}", hoje])
        pg.wait_for_url("**/resultado-despesaorcamentaria-posicao-paga", timeout=180000)
        time.sleep(5)
        txt = pg.inner_text("body")
        filtro = re.search(r"Filtrando por[^\n]*", txt)
        tot_portal = re.search(r"([\d\.]+,\d{2})\s*\n\s*Ant", txt)
        if not filtro or "Unidade" in filtro.group(0) or not tot_portal:
            raise RuntimeError(f"filtro inesperado: {filtro and filtro.group(0)}")
        pg.click("#DDO_ACTIONGROUPEXPORTContainer_btnGroupDrop"); time.sleep(0.5)
        pg.locator("#DDO_ACTIONGROUPEXPORTContainer a", has_text="CSV").click()
        for _ in range(30):  # o portal prepara o arquivo depois do clique
            time.sleep(5)
            r = ctx.request.get(PORTAL + "/wpdespesaorcamentariapagaexportcsv.aspx", timeout=180000)
            texto = r.body().decode("utf-8", "replace")
            if len(texto) > 1000:
                break
        nav.close()
    d = agregar(texto)
    d["processos"] = por_processo(texto)
    esperado = round(float(tot_portal.group(1).replace(".", "").replace(",", ".")) * 100)
    if d["total"] != esperado:
        raise RuntimeError(f"soma do CSV ({d['total']}) diferente do total do portal ({esperado})")
    d.update({"exercicio": ano, "filtro": {"considerar": "DESPESA PAGA", "emissao_de": f"01/01/{ano}", "emissao_ate": hoje,
              "total_portal": tot_portal.group(1)}, "fonte": PORTAL + "/filtros-despesasorcamentarias", "coletado_em": time.strftime("%Y-%m-%d")})
    print(f"despesas {ano}: {d['linhas']} pagamentos, R$ {d['total']/100:,.2f} (bate com o portal)")
    return d

# ---------------- compras e licitações homologadas ----------------
def _num_ano(s):
    """'5752026' -> '575/2026' (o portal exporta sem a barra; os 4 últimos dígitos são o ano)."""
    s = re.sub(r"\D", "", s or "")
    return f"{int(s[:-4])}/{s[-4:]}" if len(s) > 4 and int(s[:-4] or 0) else ""

def _data(s):
    s = re.sub(r"\D", "", s or "").zfill(8)
    return f"{s[4:8]}-{s[2:4]}-{s[0:2]}" if s.strip("0") else ""

def ler_compras(texto_csv):
    """Lê o CSV de 'Compras e Licitações' (homologadas). Alguns textos têm quebra de linha no meio."""
    linhas = texto_csv.replace("\r\n", "\n").split("\n")
    cab = [c.strip() for c in linhas[0].split(";")]
    regs, buf = [], ""
    for l in linhas[1:]:
        buf = f"{buf} {l}" if buf else l
        if buf.count(";") >= len(cab) - 1:
            regs.append([x.strip() for x in buf.split(";")]); buf = ""
    if buf.strip():
        raise RuntimeError("CSV de compras terminou no meio de um registro: " + buf[:80])
    i = {n: cab.index(n) for n in cab}
    cent = lambda v: round(float(v or 0) * 100)
    out = []
    for r in regs:
        if len(r) != len(cab):
            raise RuntimeError(f"registro com {len(r)} colunas: {';'.join(r)[:100]}")
        out.append({"modalidade": r[i["Modalidade"]], "fundamento": r[i["Fundamento Legal"]],
                     "numero": _num_ano(r[i["Número"]]), "processo": _num_ano(r[i["Processo Adm"]]),
                     "processo_id": re.sub(r"\D", "", r[i["Processo Adm"]]), "edital": _num_ano(r[i["Nº Ano Edital"]]),
                     "data": _data(r[i["Data Licitação"]]), "objeto": re.sub(r"\s+", " ", r[i["Objeto"]]),
                     "justificativa": re.sub(r"\s+", " ", r[i["Justificativa/Destinação"]]),
                     "homologado": cent(r[i["Valor Homologado"]]), "empenhado": cent(r[i["Valor Empenhado"]]),
                     "liquidado": cent(r[i["Valor Liquidado"]]), "pago": cent(r[i["Valor Pago"]]),
                     "itens": int(r[i["Qtde."]] or 0), "homologacao": r[i["Homologação"]]})
    return out

def por_processo(texto_csv_despesas):
    """Dos pagamentos (CSV de despesa paga): quanto foi pago em cada processo, a quem (só empresas) e por qual secretaria."""
    linhas = list(csv.reader(io.StringIO(texto_csv_despesas), delimiter=";"))
    cab = [c.strip() for c in linhas[0]]
    i = {n: cab.index(n) for n in ("Processo", "Unidade Orçamentária", "CPF / CNPJ", "Fornecedor", "Valor Pago")}
    P = {}
    for c in linhas[1:]:
        p = re.sub(r"\D", "", c[i["Processo"]])
        if not p or not p.strip("0"):
            continue
        v = round(float(c[i["Valor Pago"]].strip()) * 100)
        o = P.setdefault(p, {"pago": 0, "n": 0, "pf": 0, "forn": collections.Counter(), "un": collections.Counter()})
        o["pago"] += v; o["n"] += 1
        doc = c[i["CPF / CNPJ"]].strip()
        if re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", doc):
            o["forn"][f"{c[i['Fornecedor']].strip()}|{doc}"] += v
        else:
            o["pf"] += v
        o["un"][c[i["Unidade Orçamentária"]].strip()] += v
    return {p: {"pago": o["pago"], "n": o["n"], "pf": o["pf"], "forn": [[a, b] for a, b in o["forn"].most_common(5)],
                "un": [[a, b] for a, b in o["un"].most_common(3)]} for p, o in P.items()}

def compras(ano):
    """Abre o portal (Playwright), pesquisa as compras homologadas do ano e baixa o CSV oficial."""
    from playwright.sync_api import sync_playwright
    hoje = time.strftime("%d/%m/%Y") if int(time.strftime("%Y")) == ano else f"31/12/{ano}"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 (robo do Transparencia Itanhaem; coleta lenta)",
                              locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        try:
            entrar(pg)
            pg.goto(PORTAL + "/filtros-compraselicitacoes", wait_until="domcontentloaded", timeout=120000)
            pg.wait_for_selector("#vORGAO_MPAGE", timeout=90000); time.sleep(2)
            if pg.eval_on_selector("#vORGAO_MPAGE", "s => s.value") != ORGAO:
                pg.select_option("#vORGAO_MPAGE", ORGAO); time.sleep(4)
            if pg.eval_on_selector("#vEXERCICIO_MPAGE", "s => s.value") != str(ano):
                pg.select_option("#vEXERCICIO_MPAGE", str(ano)); time.sleep(4)
            pg.wait_for_selector("#W0012vDATAINICIAL", timeout=90000)
            pg.evaluate("""async ([ini, fim]) => {
              const sleep = ms => new Promise(r => setTimeout(r, ms));
              for (const [id, v] of [['W0012vDATAINICIAL', ini], ['W0012vDATAFINAL', fim]]) {
                const i = document.getElementById(id); i.focus(); i.value = v;
                i.dispatchEvent(new Event('input', {bubbles: true})); i.dispatchEvent(new Event('change', {bubbles: true})); i.blur(); await sleep(400); }
              document.getElementById('W0012BTNENTER').click();
            }""", [f"01/01/{ano}", hoje])
            pg.wait_for_url("**/resultado-compraselicitacoes", timeout=180000)
            time.sleep(5)
            pag = re.search(r"Página \d+ de (\d+)", pg.inner_text("body"))
            paginas = int(pag.group(1)) if pag else 1
            pg.click("#DDO_ACTIONGROUPEXPORTContainer_btnGroupDrop"); time.sleep(0.5)
            pg.locator("#DDO_ACTIONGROUPEXPORTContainer a", has_text="CSV").click()
            texto = ""
            for _ in range(30):
                time.sleep(4)
                texto = ctx.request.get(PORTAL + "/wpcompraslicitacoeshomologadasexportcsv.aspx", timeout=180000).body().decode("utf-8", "replace")
                if texto.count("\n") > 1:
                    break
        except Exception:
            registrar_falha(pg, "compras" if ORGAO == "2" else "itaprev-compras")
            raise
        nav.close()
    lista = ler_compras(texto)
    if not (paginas - 1) * 10 < len(lista) <= paginas * 10:
        raise RuntimeError(f"compras: {len(lista)} registros para {paginas} páginas do portal")
    print(f"compras {ano}: {len(lista)} homologadas, R$ {sum(c['homologado'] for c in lista)/100:,.2f}")
    return {"exercicio": ano, "ate": hoje, "lista": lista, "fonte": PORTAL + "/filtros-compraselicitacoes",
            "coletado_em": time.strftime("%Y-%m-%d")}

# ---------------- secretários ----------------
def secretarios():
    s = get(SITE_PREF + "/secretarias/")
    links = sorted(set(re.findall(r'href="(https://www\.itanhaem\.sp\.gov\.br/(?:secretaria-|procuradoria|chefia)[a-z0-9-]*/)"', s)))
    out = []
    for u in links:
        p = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", get(u))
        t = html.unescape(re.sub(r"<[^>]+>", "\n", p)); t = re.sub(r"[ \t\xa0]+", " ", t); t = re.sub(r"\n\s*\n+", "\n", t)
        m = re.search(r"\n(SECRETÁRI[OA]\(A\)|PROCURADOR(?:\(A\))? GERAL DO MUNICÍPIO)\s*\n(.+?)\n(.+?)\n", t)
        nome = m.group(2).strip() if m else None
        if nome and (nome.startswith("Endereço") or len(nome) > 80):
            nome = None
        out.append({"pagina": u, "cargo": "Procurador-Geral" if m and "PROCURADOR" in m.group(1) else "Secretário(a)",
                    "nome": nome, "formacao": m.group(3).strip() if nome else None})
        print(" ", u.split("/")[3], "|", nome)
    return out

def casar(unidade, secs):
    """Liga o nome da unidade orçamentária à página da secretaria (pelas palavras do nome)."""
    pal = lambda s: {w for w in re.findall(r"[A-Z]{4,}", sem_acento(s)) if w not in ("SECRETARIA", "MUNICIPAL", "FUNDO", "PUBLICAS", "PUBLICOS")}
    alvo = pal(unidade)
    melhor = max(secs, key=lambda s: len(alvo & pal(s["pagina"].replace("-", " "))), default=None)
    return melhor if melhor and len(alvo & pal(melhor["pagina"].replace("-", " "))) >= 1 else None

# ---------------- conferência com o TCE ----------------
def conferir(d):
    res = {}
    ano = d["exercicio"]
    for m in range(1, 13):
        k = f"{ano}-{m:02d}"
        if k not in d["meses"]:
            continue
        try:
            lst = json.loads(get(f"https://transparencia.tce.sp.gov.br/api/json/despesas/itanhaem/{ano}/{m}", timeout=240))
        except Exception as e:
            res[k] = {"status": "sem resposta do TCE"}; continue
        pago = sum(round(float(x["vl_despesa"].replace(".", "").replace(",", ".")) * 100) for x in lst
                   if x["orgao"].startswith("PREFEITURA") and x["evento"] == "Valor Pago")
        if not pago:
            res[k] = {"status": "TCE ainda não publicou"}
        else:
            res[k] = {"status": "bate" if abs(pago - d["meses"][k]) <= 100 else "diferente", "tce": pago, "portal": d["meses"][k]}
        print(" ", k, res[k]["status"])
    return res

def main():
    if "--itaprev" in sys.argv:
        sys.argv.remove("--itaprev"); usar_itaprev()
    cmd = sys.argv[1]
    if cmd == "despesas":
        d = despesas(int(sys.argv[3]) if len(sys.argv) > 3 else int(time.strftime("%Y")))
        json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
    elif cmd == "compras":
        d = compras(int(sys.argv[3]) if len(sys.argv) > 3 else int(time.strftime("%Y")))
        json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
    elif cmd == "aceitar-compras":  # só troca se não diminuiu
        novo = json.load(open(sys.argv[2], encoding="utf-8"))
        try:
            velho = json.load(open(sys.argv[3], encoding="utf-8"))
        except FileNotFoundError:
            velho = None
        if velho and velho["exercicio"] == novo["exercicio"] and len(novo["lista"]) < len(velho["lista"]):
            raise SystemExit(f"NÃO ACEITO: {len(novo['lista'])} compras < {len(velho['lista'])}")
        json.dump(novo, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
        print("aceito:", len(novo["lista"]), "compras")
    elif cmd == "secretarios":
        json.dump(secretarios(), open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif cmd == "aceitar":  # só troca os dados se o arquivo novo for pelo menos tão completo quanto o atual
        novo = json.load(open(sys.argv[2], encoding="utf-8"))
        try:
            velho = json.load(open(sys.argv[3], encoding="utf-8"))
        except FileNotFoundError:
            velho = None
        if velho and velho["exercicio"] == novo["exercicio"] and (novo["total"] < velho["total"] or len(novo["meses"]) < len(velho["meses"])):
            raise SystemExit(f"NÃO ACEITO: total {novo['total']} < {velho['total']} ou menos meses")
        if len(novo["unidades"]) < (10 if ORGAO == "2" else 1):
            raise SystemExit("NÃO ACEITO: poucas secretarias")
        json.dump(novo, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
        print("aceito:", novo["linhas"], "pagamentos")
    elif cmd == "conferir":
        d = json.load(open(sys.argv[2], encoding="utf-8"))
        json.dump(conferir(d), open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
