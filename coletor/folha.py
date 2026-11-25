"""Folha de pagamento da Câmara de Itanhaém (Portal da Transparência, sistema GCASP).

O portal só funciona dentro de um navegador, então este coletor usa o Playwright (Chromium).
Nomes NÃO são gravados: só matrícula (para somar o ano da mesma pessoa), cargo e valores.
A matrícula fica no arquivo de dados e nunca vai para o site.

Uso: python folha.py <saida.json> [exercicio]
Requer: pip install playwright && python -m playwright install --with-deps chromium
"""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "https://transparencia.itanhaem.sp.leg.br/filtros-recursoshumanos"

# Mesmo código testado à mão no navegador em 24/11/2026.
JS_MESES = """async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (let k = 0; k < 60 && !document.getElementById('W0012COMBO_MESContainer_btnGroupDrop'); k++) await sleep(250);
  await sleep(800);
  document.getElementById('W0012COMBO_MESContainer_btnGroupDrop').click(); await sleep(700);
  const ms = [...document.querySelectorAll('a.ExtendedComboLevel0')].map(a => a.innerText.trim());
  document.body.click();
  return ms;
}"""
JS_ESCOLHER = """async (m) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (let k = 0; k < 60 && !document.getElementById('W0012COMBO_MESContainer_btnGroupDrop'); k++) await sleep(250);
  await sleep(800);
  document.getElementById('W0012COMBO_MESContainer_btnGroupDrop').click(); await sleep(700);
  [...document.querySelectorAll('a.ExtendedComboLevel0')].find(a => a.innerText.trim() == m).click(); await sleep(1500);
  [...document.querySelectorAll('input[type=button],input[type=submit],button,a')].find(b => /Confirmar/i.test(b.value || b.innerText || '')).click();
  return m;
}"""
JS_LER = r"""async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (let k = 0; k < 120 && !/resultado/.test(location.href); k++) await sleep(250);
  await sleep(2500);
  const grab = () => [...document.querySelectorAll('tr')].filter(r => r.cells.length > 15 && /^\d+$/.test(r.cells[1].innerText.trim()))
    .map(r => { const c = [...r.cells].slice(1, 21).map(c => c.innerText.trim());
                return [c[0], c[2], c[6], c[8], c[12], c[13], c[14], c[15], c[16], c[17], c[18], c[19]]; });
  const lab = () => { const m = document.body.innerText.match(/Página (\d+) de (\d+)/); return m ? [+m[1], +m[2]] : null; };
  let all = [];
  for (let i = 0; i < 60; i++) {
    const g = grab(); all.push(...g); const L = lab(); if (!L || L[0] >= L[1]) break;
    const first = g[0][0]; document.querySelector('li.next a').click();
    for (let k = 0; k < 80; k++) { await sleep(250); const h = grab(); if (h.length && h[0][0] !== first) break; }
  }
  const mes = (document.body.innerText.match(/Mês\n(\S+)/) || [])[1];
  return {mes, pag: lab(), rows: all};
}"""

def abrir(pg):
    """Abre a página de filtros e espera o botão do mês aparecer (o portal nunca fica 'quieto' na rede)."""
    pg.goto(URL, wait_until="domcontentloaded", timeout=120000)
    try:
        pg.wait_for_selector("#W0012COMBO_MESContainer_btnGroupDrop", timeout=90000)
    except Exception:
        registrar_falha(pg, "folha-abrir")
        raise
    time.sleep(2)

def registrar_falha(pg, nome):
    """Guarda print e HTML da página em dados/registro/ para entender o erro."""
    import os
    os.makedirs("dados/registro", exist_ok=True)
    try:
        pg.screenshot(path=f"dados/registro/{nome}.png", full_page=True)
        open(f"dados/registro/{nome}.html", "w", encoding="utf-8").write(pg.content()[:300000])
        print("  falha registrada:", nome, pg.url, file=sys.stderr)
    except Exception as e:
        print("  não consegui registrar a falha:", e, file=sys.stderr)

def num(s):
    return round(float(s.replace(".", "").replace(",", ".")) * 100)

def anonimizar(meses):
    """Troca a matrícula por um número interno (1, 2, 3...) sorteado a cada coleta.
    Serve só para somar os meses da mesma pessoa; não permite achar ninguém."""
    import random
    mats = sorted({r[0] for rows in meses.values() for r in rows})
    novos = list(range(1, len(mats) + 1)); random.shuffle(novos)
    troca = dict(zip(mats, novos))
    for rows in meses.values():
        for r in rows:
            r[0] = troca[r[0]]

def coletar(exercicio):
    D = {"o": [], "f": [], "v": []}
    ix = lambda k, s: D[k].index(s) if s in D[k] else (D[k].append(s) or len(D[k]) - 1)
    meses = {}
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 (robo do Transparencia Itanhaem; coleta lenta)", locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={"width": 1366, "height": 900})
        abrir(pg)
        if str(exercicio) != pg.eval_on_selector("#vEXERCICIO_MPAGE", "s => s.value"):
            pg.select_option("#vEXERCICIO_MPAGE", str(exercicio)); time.sleep(5)
        lista = [m for m in pg.evaluate(JS_MESES) if "13" not in m]
        print("meses disponíveis:", lista)
        for m in lista:
            for tentativa in range(3):
                try:
                    abrir(pg)
                    pg.evaluate(JS_ESCOLHER, m)
                    pg.wait_for_url("**/resultado-recursoshumanos", timeout=60000)
                    r = pg.evaluate(JS_LER)
                    if r["mes"] != m or not r["pag"] or r["pag"][0] != r["pag"][1]:
                        raise RuntimeError(f"leitura incompleta: {r['mes']} {r['pag']}")
                    paginas = r["pag"][1]
                    if not (paginas - 1) * 5 < len(r["rows"]) <= paginas * 5:
                        raise RuntimeError(f"{m}: {len(r['rows'])} linhas para {paginas} páginas")
                    meses[m] = [[int(x[0]), ix("o", x[1]), ix("f", x[2]), ix("v", x[3])] + [num(v) for v in x[4:]] for x in r["rows"]]
                    print(" ", m, len(meses[m]), "pessoas")
                    break
                except Exception as e:
                    print("  tentativa", tentativa + 1, m, e, file=sys.stderr); time.sleep(10)
            else:
                registrar_falha(pg, "folha-" + m)
                raise RuntimeError("não consegui ler " + m)
        nav.close()
    anonimizar(meses)
    return {"dic": D, "cols": "id_interno,org,funcao,vinculo,base,desc,vant,ferias,apos,bolsa,pensao,liq (centavos)",
            "meses": meses, "fonte": URL, "exercicio": exercicio, "coletado_em": time.strftime("%Y-%m-%d")}

def main():
    saida = sys.argv[1]
    ano = int(sys.argv[2]) if len(sys.argv) > 2 else int(time.strftime("%Y"))
    d = coletar(ano)
    if not d["meses"]:  # janeiro, antes da primeira folha do ano
        d = coletar(ano - 1)
    json.dump(d, open(saida, "w", encoding="utf-8"), ensure_ascii=False)
    print("ok", d["exercicio"], list(d["meses"]))

if __name__ == "__main__":
    main()
