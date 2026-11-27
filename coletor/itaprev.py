"""Raio-X do ITAPREV (Itanhaém Prev, instituto de previdência dos servidores municipais).

Fonte desta parte: API de transparência do TCE-SP (dados que os órgãos enviam ao Tribunal pelo AUDESP).
  - receitas e despesas do instituto, mês a mês
  - quanto a Prefeitura e a Câmara pagaram ao instituto em cada mês (contribuições patronais,
    contribuições descontadas dos servidores, parcelamentos e aportes)

Nenhum nome de pessoa física vai para o site: só empresas (CNPJ) e totais.

Uso: python itaprev.py tce <saida.json> [ano]
"""
import collections, json, re, sys, time, urllib.request

UA = "RadarItanhaem/0.1 (projeto civico de transparencia; coleta lenta)"
TCE = "https://transparencia.tce.sp.gov.br/api/json"

def get_json(url, tentativas=4):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=240) as r:
                d = json.loads(r.read())
            time.sleep(2)
            return d
        except Exception as e:
            print("  erro", url, e, file=sys.stderr); time.sleep(15 * (t + 1))
    raise RuntimeError("TCE sem resposta: " + url)

CNPJ_ITAPREV = "08424027000113"
valor = lambda s: round(float(str(s).replace(".", "").replace(",", ".")) * 100)
eh_prev = lambda s: "PREV" in (s or "").upper()

def tce(ano):
    ultimo = int(time.strftime("%m")) if int(time.strftime("%Y")) == ano else 12
    meses = {}
    for m in range(1, ultimo + 1):
        k = f"{ano}-{m:02d}"
        desp = get_json(f"{TCE}/despesas/itanhaem/{ano}/{m}")
        rec = get_json(f"{TCE}/receitas/itanhaem/{ano}/{m}")
        if not desp and not rec:
            print(" ", k, "TCE ainda não publicou"); continue
        ita_pago, ita_emp = 0, 0
        forn_pj = collections.Counter()
        repasse = collections.Counter()  # quem pagou ao instituto
        for x in desp:
            ev, org = x["evento"], x["orgao"]
            v = valor(x["vl_despesa"])
            if eh_prev(org):
                if ev == "Valor Pago":
                    ita_pago += v
                    doc = x.get("id_fornecedor", "")
                    if "CNPJ" in doc and not eh_prev(x.get("nm_fornecedor")):
                        forn_pj[f"{x['nm_fornecedor'].strip()}|{doc.split('-')[-1].strip()}"] += v
                elif ev == "Empenhado":
                    ita_emp += v
            elif ev == "Valor Pago" and CNPJ_ITAPREV in re.sub(r"\D", "", x.get("id_fornecedor", "")):
                repasse["Prefeitura" if org.startswith("PREFEITURA") else "Câmara" if org.startswith("C") else org] += v
        receitas = collections.Counter()
        for x in rec:
            if eh_prev(x.get("orgao")):
                cat = (x.get("ds_alinea") or x.get("ds_subalinea") or "Outras").strip()
                receitas[cat] += valor(x.get("vl_arrecadacao", "0"))
        if not ita_pago and not receitas:
            print(" ", k, "TCE ainda não publicou o ITAPREV"); continue
        meses[k] = {"pago": ita_pago, "empenhado": ita_emp, "receitas": dict(receitas), "receita_total": sum(receitas.values()),
                    "repasses": dict(repasse), "fornecedores_pj": [[a, b] for a, b in forn_pj.most_common(15)]}
        print(f"  {k}: entrou R$ {sum(receitas.values())/100:,.2f} | saiu R$ {ita_pago/100:,.2f} | repasses {({a: round(b/100) for a, b in repasse.items()})}")
    return {"exercicio": ano, "meses": meses, "fonte": "https://transparencia.tce.sp.gov.br", "coletado_em": time.strftime("%Y-%m-%d")}

JS_LER_FOLHA = r"""async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const num = s => Math.round(parseFloat((s||'0').replace(/\./g,'').replace(',','.'))*100) || 0;
  const grab = () => [...document.querySelectorAll('tr')].filter(r => r.cells.length > 15 && /^\d+$/.test(r.cells[1].innerText.trim()))
    .map(r => { const c = [...r.cells].map(x => x.innerText.trim());   // c[2] (nome) é ignorado de propósito
      return {mat: c[1], org: c[3], fun: c[7], ref: num(c[13]), vant: num(c[14]), liq: num(c[16])}; });
  const lab = () => { const m = document.body.innerText.match(/Página (\d+) de (\d+)/); return m ? [+m[1], +m[2]] : null; };
  let all = [];
  for (let i = 0; i < 400; i++) {
    const g = grab(); all.push(...g); const L = lab(); if (!L || L[0] >= L[1]) break;
    const first = g[0].mat; document.querySelector('li.next a').click();
    for (let k = 0; k < 120; k++) { await sleep(150); const h = grab(); if (h.length && h[0].mat !== first) break; }
  }
  const mes = (document.body.innerText.match(/Mês\n(\S+)/) || [])[1];
  return {mes, pag: lab(), rows: all};
}"""

def resumir_folha(rows, mes, ano):
    """Agrega a folha do instituto sem guardar nomes nem matrículas."""
    bruto = lambda r: r["ref"] + r["vant"]
    def tipo(r):
        o = r["org"].upper()
        return "Aposentados" if o.startswith("APOSENTADO") else "Pensionistas" if o.startswith("PENSIONISTA") else "Estagiários" if "ESTAGI" in o else "Equipe do instituto"
    plano = lambda r: "plano previdenciário" if "PREVIDENCI" in r["org"].upper() else "plano financeiro" if "FINANCEIRO" in r["org"].upper() else ""
    G = {}
    for r in rows:
        g = G.setdefault(tipo(r), {"nome": tipo(r), "pessoas": 0, "total": 0, "liq": 0})
        g["pessoas"] += 1; g["total"] += bruto(r); g["liq"] += r["liq"]
    grupos = sorted([{**g, "media_bruto": round(g["total"] / g["pessoas"])} for g in G.values() if g["nome"] != "Estagiários"], key=lambda g: -g["pessoas"])
    ben = [r for r in rows if tipo(r) in ("Aposentados", "Pensionistas")]
    lim = [(0, 200000, "até R$ 2 mil"), (200000, 500000, "de R$ 2 mil a R$ 5 mil"), (500000, 1000000, "de R$ 5 mil a R$ 10 mil"),
           (1000000, 2000000, "de R$ 10 mil a R$ 20 mil"), (2000000, 3000000, "de R$ 20 mil a R$ 30 mil"), (3000000, 10**12, "acima de R$ 30 mil")]
    faixas = [{"nome": n, "n": sum(1 for r in ben if a <= bruto(r) < b)} for a, b, n in lim]
    maiores = [{"tipo": f"{'Aposentado(a)' if tipo(r) == 'Aposentados' else 'Pensionista'} · {plano(r)}", "bruto": bruto(r)}
               for r in sorted(ben, key=lambda r: -bruto(r))[:10]]
    E = {}
    for r in rows:
        if tipo(r) == "Equipe do instituto":
            e = E.setdefault(r["fun"], {"funcao": r["fun"], "pessoas": 0, "total": 0}); e["pessoas"] += 1; e["total"] += bruto(r)
    equipe = sorted([{"funcao": e["funcao"], "pessoas": e["pessoas"], "media_bruto": round(e["total"] / e["pessoas"])} for e in E.values()], key=lambda e: -e["media_bruto"])
    vals = sorted(bruto(r) for r in ben)
    return {"mes": mes, "exercicio": ano, "pessoas": len(rows), "grupos": grupos, "faixas": faixas, "maiores": maiores, "equipe": equipe,
            "estagiarios": sum(1 for r in rows if tipo(r) == "Estagiários"), "beneficios_total": sum(vals),
            "beneficio_medio": round(sum(vals) / len(vals)) if vals else 0, "mediana": vals[len(vals) // 2] if vals else 0,
            "fonte": "https://transparenciaonline.gcaspp.com/filtros-recursoshumanos", "coletado_em": time.strftime("%Y-%m-%d")}

def folha(ano):
    """Folha do mês mais recente do instituto (Playwright). Entra pelo portal da Prefeitura escolhendo o ITAPREV."""
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import prefeitura as P
    from playwright.sync_api import sync_playwright
    P.usar_itaprev()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 (robo do Transparencia Itanhaem; coleta lenta)",
                              locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        try:
            P.entrar(pg)
            pg.goto(P.PORTAL + "/filtros-recursoshumanos", wait_until="domcontentloaded", timeout=120000)
            pg.wait_for_selector("#W0012COMBO_MESContainer_btnGroupDrop", timeout=90000); time.sleep(2)
            pg.click("#W0012COMBO_MESContainer_btnGroupDrop"); time.sleep(1)
            meses = [m for m in pg.eval_on_selector_all("a.ExtendedComboLevel0", "as => as.map(a => a.innerText.trim())") if "13" not in m]
            mes = meses[-1]
            pg.locator("a.ExtendedComboLevel0", has_text=mes).first.click(); time.sleep(1.5)
            pg.locator("input[value='Confirmar'], button:has-text('Confirmar'), a:has-text('Confirmar')").first.click()
            pg.wait_for_url("**/resultado-recursoshumanos", timeout=120000); time.sleep(3)
            r = pg.evaluate(JS_LER_FOLHA)
        except Exception:
            P.registrar_falha(pg, "itaprev-folha")
            raise
        nav.close()
    paginas = r["pag"][1] if r["pag"] else 1
    if not (paginas - 1) * 5 < len(r["rows"]) <= paginas * 5:
        raise RuntimeError(f"folha ITAPREV: {len(r['rows'])} linhas para {paginas} páginas")
    d = resumir_folha(r["rows"], r["mes"] or mes, ano)
    print(f"folha ITAPREV {d['mes']}: {d['pessoas']} pessoas")
    return d

def main():
    if sys.argv[1] == "folha":
        ano = int(sys.argv[3]) if len(sys.argv) > 3 else int(time.strftime("%Y"))
        json.dump(folha(ano), open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
        return
    if sys.argv[1] == "tce":
        ano = int(sys.argv[3]) if len(sys.argv) > 3 else int(time.strftime("%Y"))
        d = tce(ano)
        if not d["meses"]:
            raise SystemExit("nenhum mês publicado pelo TCE")
        json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)

if __name__ == "__main__":
    main()
