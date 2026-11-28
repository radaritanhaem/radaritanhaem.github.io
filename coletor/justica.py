"""Precatórios da Prefeitura de Itanhaém: dívidas que a Justiça mandou pagar e ainda estão na fila.

Fonte oficial e sem verificação anti-robô: Relatório de Gestão Fiscal (RGF), Anexo 2 (Dívida Consolidada),
que a Prefeitura entrega ao Tesouro Nacional (SICONFI) a cada quadrimestre. A linha usada é
"Precatórios Posteriores a 05/05/2000 (inclusive) Vencidos e Não Pagos".

(A lista nominal de precatórios do TJSP tem CAPTCHA e nomes de credores; não é usada.)
Os pagamentos feitos por decisão judicial vêm de prefeitura.py (campo "justica" de prefeitura_despesas.json).

Uso: python coletor/justica.py dados/prefeitura_precatorios.json [ano]
"""
import json, sys, time, urllib.request

IBGE = 3522109
API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf"
UA = "Mozilla/5.0 (robo do Transparencia Itanhaem)"

def rgf(ano, quad):
    url = (f"{API}?an_exercicio={ano}&in_periodicidade=Q&nr_periodo={quad}&co_tipo_demonstrativo=RGF"
           f"&no_anexo=RGF-Anexo%2002&co_esfera=M&co_poder=E&id_ente={IBGE}")
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return json.load(r).get("items", []), url
        except Exception as e:
            print("  erro SICONFI", e, file=sys.stderr); time.sleep(8 * (t + 1))
    raise RuntimeError("SICONFI não respondeu")

def coletar(ano):
    for quad in (3, 2, 1):
        itens, url = rgf(ano, quad)
        prec = [x for x in itens if x.get("cod_conta") == "PrecatoriosPosterioresA05052000VencidosENaoPagos"]
        if prec:
            break
    else:
        raise RuntimeError(f"nenhum RGF de {ano} publicado ainda")
    dc = {x["coluna"]: x["valor"] for x in itens if x.get("cod_conta") == "DividaConsolidada"}
    serie = [{"quando": x["coluna"], "valor": round(x["valor"] * 100)} for x in prec]
    return {"exercicio": ano, "quadrimestre": quad, "instituicao": itens[0].get("instituicao"), "serie": serie,
            "divida_consolidada": {k: round(v * 100) for k, v in dc.items()},
            "fonte": "https://siconfi.tesouro.gov.br", "consulta": url, "coletado_em": time.strftime("%Y-%m-%d")}

if __name__ == "__main__":
    ano = int(sys.argv[2]) if len(sys.argv) > 2 else int(time.strftime("%Y"))
    d = coletar(ano)
    if not d["serie"]:
        raise SystemExit("precatórios vieram vazios: mantendo o arquivo anterior")
    json.dump(d, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"precatórios {ano} (RGF {d['quadrimestre']}º quadr.): " + ", ".join(f"{s['quando']}: R$ {s['valor']/100:,.2f}" for s in d["serie"]))
