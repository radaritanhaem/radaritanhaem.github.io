"""Acrescenta FOLHA DE PAGAMENTO e LICITAÇÕES ao dados-site.json.

Regras:
  - Folha: nenhum nome e nenhuma matrícula vão para o site. Só cargo, mês e valores publicados.
  - "Bruto" = salário base + vencimentos e demais vantagens + férias + aposentadoria + pensão
    (bolsa de estágio já está dentro de "vantagens" no portal, por isso não é somada de novo).
  - Valores copiados como o portal publica; quando a conta do próprio portal não fecha, avisamos.

Uso: python processar_extra.py <folha.json> <licitacoes.json> <dados-site.json>
"""
import collections, json, statistics, sys

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO",
         "OUTUBRO", "NOVEMBRO", "DEZEMBRO", "13º SALÁRIO"]
GRUPO = {"ASSESSORES": "Comissionados (assessores e chefes)", "ADMINISTRAÇÃO": "Diretores e servidores da administração",
         "VEREADORES": "Vereadores", "ESTAGIÁRIOS": "Estagiários",
         "APOSENTADOS PARLAMENTAR": "Ex-vereadores aposentados", "PENSIONISTAS PARLAMENTAR": "Pensionistas de ex-vereadores"}

def cargo_bonito(s):
    s = s.capitalize()
    for a, b in [("camara", "Câmara"), ("câmara", "Câmara"), ("presidencia", "Presidência"), ("publicas", "Públicas"),
                 ("patrimonio", "Patrimônio"), ("estagiario", "Estagiário"), ("tecnologia da informação e comunicação", "TI e Comunicação")]:
        s = s.replace(a, b)
    return s

def folha(f):
    D = f["dic"]; R = lambda c: round(c / 100, 2)
    meses = [m for m in MESES if m in f["meses"]]
    linhas = []  # (mes, mat, org, funcao, vinculo, base, desc, vant, fer, apo, bolsa, pen, liq, bruto)
    nao_fecha = 0
    for m in meses:
        for mat, o, fu, vi, base, desc, vant, fer, apo, bol, pen, liq in f["meses"][m]:
            bruto = base + vant + fer + apo + pen
            if bruto + desc != liq:
                nao_fecha += 1
            linhas.append((m, mat, D["o"][o], D["f"][fu], D["v"][vi], base, desc, vant, fer, apo, bol, pen, liq, bruto))
    ult = meses[-1]
    por_mes = []
    for m in meses:
        L = [l for l in linhas if l[0] == m]
        por_mes.append({"m": m.capitalize(), "pessoas": len(L), "bruto": R(sum(l[13] for l in L)), "liq": R(sum(l[12] for l in L))})
    grupos = []
    for org, nome in GRUPO.items():
        L = [l for l in linhas if l[2] == org]
        Lu = [l for l in L if l[0] == ult]
        if L:
            grupos.append({"nome": nome, "pessoas": len(Lu), "bruto_ano": R(sum(l[13] for l in L)), "bruto_ult": R(sum(l[13] for l in Lu))})
    grupos.sort(key=lambda g: -g["bruto_ano"])
    # por cargo
    cargos = []
    por_f = collections.defaultdict(list)
    for l in linhas:
        por_f[l[3]].append(l)
    for fu, L in por_f.items():
        Lu = [l for l in L if l[0] == ult]
        bases = [l[5] for l in L if l[5] > 0]
        pessoas_ano = len({l[1] for l in L})
        pm = len(L)  # pessoas x meses
        maior = max(L, key=lambda l: l[13])
        cargos.append({"cargo": cargo_bonito(fu), "grupo": GRUPO.get(L[0][2], L[0][2]), "pessoas": len(Lu), "pessoas_ano": pessoas_ano,
                       "base_tipica": R(statistics.median(bases)) if bases else 0,
                       "media_bruto": R(sum(l[13] for l in L) / pm), "media_liq": R(sum(l[12] for l in L) / pm),
                       "extras_ano": R(sum(l[7] + l[8] for l in L)), "bruto_ano": R(sum(l[13] for l in L)),
                       "maior": R(maior[13]), "maior_mes": maior[0].capitalize(),
                       "vinculo": L[0][4]})
    cargos.sort(key=lambda c: -c["media_bruto"])
    # meses em que o total passou do dobro do salario base (sem nome, sem matricula)
    destaques = []
    for l in linhas:
        m, mat, org, fu, vi, base, desc, vant, fer, apo, bol, pen, liq, bruto = l
        if base > 0 and bruto >= 2 * base and bruto >= 2000000:
            destaques.append({"cargo": cargo_bonito(fu), "mes": m.capitalize(), "base": R(base), "vant": R(vant), "ferias": R(fer),
                              "bruto": R(bruto), "liq": R(liq), "vezes": round(bruto / base, 1)})
    destaques.sort(key=lambda d: -d["bruto"])
    # por pessoa no ano, identificada so pelo cargo (sem nome/matricula)
    anual = []
    por_mat = collections.defaultdict(list)
    for l in linhas:
        por_mat[l[1]].append(l)
    for mat, L in por_mat.items():
        L.sort(key=lambda l: MESES.index(l[0]))
        org = L[-1][2]
        if org in ("ESTAGIÁRIOS",):
            continue
        anual.append({"cargo": cargo_bonito(L[-1][3]), "grupo": GRUPO.get(org, org), "meses": len(L),
                      "base": R(sum(l[5] for l in L)), "extras": R(sum(l[7] + l[8] for l in L)),
                      "bruto": R(sum(l[13] for l in L)), "liq": R(sum(l[12] for l in L)),
                      "serie": [R(l[13]) for l in L], "serie_meses": [l[0][:3].capitalize() for l in L]})
    anual.sort(key=lambda a: -a["bruto"])
    total = R(sum(l[13] for l in linhas))
    print(f"folha: {len(linhas)} linhas, {len(meses)} meses, bruto {total:,.2f}, {len(destaques)} destaques, contas que nao fecham: {nao_fecha}")
    return {"exercicio": f["exercicio"], "meses": por_mes, "de": meses[0].capitalize(), "ate": ult.capitalize(),
            "total_bruto": total, "total_liq": R(sum(l[12] for l in linhas)), "pessoas_ult": por_mes[-1]["pessoas"],
            "grupos": grupos, "cargos": cargos, "destaques": destaques[:40], "n_destaques": len(destaques),
            "anual": anual, "nao_fecha": nao_fecha, "fonte": f["fonte"], "coletado_em": f["coletado_em"]}

def licitacoes(d):
    out = []
    for l in d["licitacoes"]:
        p = l.get("pncp_dados") or {}
        hom = p.get("homologado") or p.get("homologado_soma_itens")
        out.append({"id": l["id"], "data": l["data"], "titulo": l["titulo"], "objeto": l["objeto"],
                    "modalidade": l["modalidade"], "etapa": l["etapa"], "processo": l["processo"],
                    "pncp": l["pncp"], "estimado": p.get("estimado"), "homologado": hom,
                    "situacao": p.get("situacao"), "amparo": p.get("amparo"),
                    "vencedores": [{"nome": v["nome"], "cnpj": v["cnpj"], "valor": round(v["valor"], 2)} for v in p.get("vencedores", [])][:6],
                    "anexos": l["anexos"]})
    out.sort(key=lambda x: x["data"][-4:] + x["data"][3:5] + x["data"][:2], reverse=True)
    forn = collections.defaultdict(lambda: {"valor": 0.0, "n": 0})
    for l in out:
        for v in l["vencedores"]:
            if v["cnpj"]:
                k = (v["nome"], v["cnpj"]); forn[k]["valor"] += v["valor"]; forn[k]["n"] += 1
    fornecedores = [{"nome": k[0], "cnpj": k[1], "valor": round(v["valor"], 2), "n": v["n"]}
                    for k, v in sorted(forn.items(), key=lambda kv: -kv[1]["valor"])][:15]
    modal = collections.Counter(l["modalidade"] or "Não informada" for l in out)
    com_valor = [l for l in out if l["homologado"]]
    print(f"licitacoes: {len(out)} | com valor homologado: {len(com_valor)} | fornecedores: {len(forn)}")
    return {"lista": out, "fornecedores": fornecedores, "modalidades": modal.most_common(),
            "total_homologado": round(sum(l["homologado"] for l in com_valor), 2),
            "total_estimado": round(sum(l["estimado"] or 0 for l in com_valor), 2),
            "n_valor": len(com_valor), "desde": d["ano_min"], "total_portal": d["total_portal"], "coletado_em": d["coletado_em"]}

def main():
    f = json.load(open(sys.argv[1], encoding="utf-8"))
    li = json.load(open(sys.argv[2], encoding="utf-8"))
    site = json.load(open(sys.argv[3], encoding="utf-8"))
    site["folha"] = folha(f)
    site["licitacoes"] = licitacoes(li)
    json.dump(site, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()
