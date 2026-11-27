"""Entidades sem fins lucrativos (associações, fundações, institutos, organizações religiosas...) que
RECEBERAM dinheiro da Prefeitura no ano (só valor PAGO, nunca empenho).

Como acha as entidades sem depender do nome:
  1. prefeitura.py guarda o total pago a cada CNPJ (campo "pj" de dados/prefeitura_despesas.json);
  2. cada CNPJ é conferido no cadastro público da Receita Federal (natureza jurídica), via minhareceita.org / BrasilAPI;
  3. ficam as naturezas do grupo 3 ("Entidades sem fins lucrativos"), menos cartórios e condomínios.

O cadastro já consultado fica em dados/cnpj_receita.json (só código e descrição da natureza jurídica),
então cada dia só os CNPJs novos são consultados.

Uso: python coletor/entidades.py dados/prefeitura_despesas.json dados/prefeitura_entidades.json
"""
import collections, json, os, re, sys, time, urllib.error, urllib.request

CACHE = "dados/cnpj_receita.json"
APIS = ["https://minhareceita.org/", "https://brasilapi.com.br/api/cnpj/v1/"]  # cadastro público da Receita (o segundo é reserva)
UA = "Mozilla/5.0 (robo do Transparencia Itanhaem; consulta lenta)"
FORA = {"3034", "3085"}  # serviço notarial (cartório) e condomínio edilício: não são entidades da sociedade civil

def tipo(codigo, descricao):
    c = str(codigo or "")
    if not c.startswith("3") or c in FORA:
        return None
    return {"3999": "Associação", "3069": "Fundação privada", "3220": "Organização religiosa", "3301": "Organização Social (OS)",
            "3131": "Sindicato / entidade sindical", "3077": "Serviço Social Autônomo (Sistema S)", "3247": "Fundo privado"}.get(c, descricao or "Sem fins lucrativos")

def consultar(cnpj):
    for t in range(6):
        api = APIS[t % len(APIS)]
        try:
            with urllib.request.urlopen(urllib.request.Request(api + cnpj, headers={"User-Agent": UA}), timeout=60) as r:
                j = json.load(r)
            return [j.get("codigo_natureza_juridica"), j.get("natureza_juridica")]  # só a natureza; sócios e endereço não são guardados
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return [0, "não encontrado"]
        except Exception:
            pass
        time.sleep(4 * (t + 1))
    return None

def montar(desp_path, out_path):
    d = json.load(open(desp_path, encoding="utf-8"))
    pj = d.get("pj")
    if not pj:
        print("prefeitura_despesas.json ainda não tem o total por CNPJ (campo 'pj'): a lista de entidades fica como está")
        return
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    novos = falhas = 0
    for doc in pj:
        c = re.sub(r"\D", "", doc)
        if c not in cache:
            r = consultar(c); time.sleep(0.6)
            if r is None:
                falhas += 1
                print("  sem resposta do cadastro para", doc, file=sys.stderr); continue
            cache[c] = r; novos += 1
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    if falhas > max(5, len(pj) // 20):
        raise SystemExit(f"{falhas} CNPJs sem resposta do cadastro: a lista não foi refeita (fica a última boa)")
    # matriz e filiais (mesma raiz de 8 dígitos) são a mesma entidade: a Prefeitura às vezes estorna de uma e paga na outra
    G = {}
    soma = lambda a, b: [[k, v] for k, v in sorted((collections.Counter(dict(a)) + collections.Counter(dict(b))).items(), key=lambda kv: -kv[1])]
    for doc, e in pj.items():
        nj = cache.get(re.sub(r"\D", "", doc))
        t = nj and tipo(nj[0], nj[1])
        if not t:
            continue
        g = G.setdefault(doc[:10], {"cnpj": doc, "nome": e["nome"], "tipo": t, "natureza_juridica": nj[1], "pago": 0, "n": 0,
                                    "un": [], "nat": [], "mes": {}, "mod": [], "obj": [], "_maior": None})
        if g["_maior"] is None or e["tot"] > g["_maior"]:
            g.update(cnpj=doc, nome=e["nome"], _maior=e["tot"])
        g["pago"] += e["tot"]; g["n"] += e["n"]
        for k in ("un", "nat", "mod", "obj"):
            g[k] = soma(g[k], e.get(k, []))
        for m, v in e["mes"].items():
            g["mes"][m] = g["mes"].get(m, 0) + v
    ent = []
    for g in G.values():
        g.pop("_maior")
        g["mes"] = {m: v for m, v in g["mes"].items() if v > 0}
        for k in ("un", "nat", "mod", "obj"):
            g[k] = [[a, b] for a, b in g[k] if b > 0][:5]
        if g["pago"] > 0:
            ent.append(g)
    ent.sort(key=lambda x: -x["pago"])
    out = {"exercicio": d.get("exercicio"), "coletado_em": d.get("coletado_em"), "fonte": d.get("fonte"),
           "cadastro": "Receita Federal (natureza jurídica), via minhareceita.org / BrasilAPI", "total": sum(x["pago"] for x in ent),
           "cnpjs_conferidos": len(pj), "entidades": ent}
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"entidades {out['exercicio']}: {len(ent)} sem fins lucrativos de {len(pj)} CNPJs, R$ {out['total']/100:,.2f} pagos ({novos} CNPJs novos consultados)")

if __name__ == "__main__":
    montar(sys.argv[1], sys.argv[2])
