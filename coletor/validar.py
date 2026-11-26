"""Confere os dados novos antes de publicar. Se algo parecer estranho, sai com erro
e o robô NÃO publica: o site continua com a última versão boa.

Uso: python validar.py <dados-site anterior.json> <dados-site novo.json>
"""
import json, sys

def main():
    ant = json.load(open(sys.argv[1], encoding="utf-8"))
    nov = json.load(open(sys.argv[2], encoding="utf-8"))
    erros = []
    def checa(cond, msg):
        if not cond: erros.append(msg)

    checa(9 <= len(nov.get("vereadores", [])) <= 11, f"número de vereadores estranho: {len(nov.get('vereadores', []))}")
    checa(len(nov.get("props", [])) >= 0.97 * len(ant.get("props", [])),
          f"propostas caíram de {len(ant.get('props', []))} para {len(nov.get('props', []))}")
    checa(len(nov.get("sessoes", [])) >= len(ant.get("sessoes", [])),
          f"sessões caíram de {len(ant.get('sessoes', []))} para {len(nov.get('sessoes', []))}")
    checa(all(v.get("foto") for v in nov.get("vereadores", [])), "vereador sem foto")
    # presença: se há sessões com relatório, os vereadores precisam ter presença lida (e o total não pode cair)
    pres = lambda d: sum(sum(v.get("pres", {}).values()) for v in d.get("vereadores", []))
    if nov.get("sessoes"):
        checa(pres(nov) > 0, "presença vazia: os relatórios de presença não foram lidos")
        checa(pres(nov) >= pres(ant), f"registros de presença caíram de {pres(ant)} para {pres(nov)}")
    checa(nov.get("salario", {}).get("mensal", 0) > 0, "salário zerado")

    fa, fn = ant.get("folha"), nov.get("folha")
    checa(bool(fn), "folha sumiu")
    if fa and fn:
        if fa["exercicio"] == fn["exercicio"]:
            checa(len(fn["meses"]) >= len(fa["meses"]), f"folha perdeu meses: {len(fa['meses'])} -> {len(fn['meses'])}")
        for m in fn["meses"]:
            checa(40 <= m["pessoas"] <= 200, f"folha de {m['m']} com {m['pessoas']} pessoas")

    la, ln = ant.get("licitacoes"), nov.get("licitacoes")
    checa(bool(ln), "licitações sumiram")
    if la and ln:
        checa(len(ln["lista"]) >= len(la["lista"]), f"licitações caíram de {len(la['lista'])} para {len(ln['lista'])}")

    if erros:
        print("NÃO PUBLICAR:"); [print(" -", e) for e in erros]; sys.exit(1)
    print(f"ok: {len(nov['props'])} propostas, {len(nov['sessoes'])} sessões, "
          f"folha {len(fn['meses'])} meses, {len(ln['lista'])} licitações")

if __name__ == "__main__":
    main()
