"""Transforma dados.json (coleta bruta) em dados-site.json (o que o site mostra).

Todas as regras de classificacao ficam aqui, iguais para todos os vereadores.
Uso: python processar.py <dados.json> <saida/dados-site.json>
"""
import json, re, sys, unicodedata, collections

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

# ---------- Passo 3: grupos que qualquer pessoa entende ----------
HOMENAGEM = re.compile(r"aplauso|congratula|parabeniz|louvor|pesar|falecimento|condolen|titulo (de )?cidad|cidadao (honorario|itanhaense)|cidadania|medalha|comenda|honra ao merito|diploma|denomina|da nome|dar nome|homenage|data comemorativa|calendario oficial|institui o dia|institui a semana|institui o mes|utilidade publica")
def grupo(tipo, ementa):
    t, e = sem_acento(tipo), re.sub(r"\s+", " ", sem_acento(ementa))
    if t.startswith("indica"):
        return "melhoria"
    if t.startswith("requerimento"):
        return "cobranca"
    if t.startswith("mo"):  # Mocao
        return "homenagem" if HOMENAGEM.search(e) or "repudio" not in e else "outros"
    if HOMENAGEM.search(e):
        return "homenagem"
    if t.startswith("projeto") or t.startswith("substitutivo"):
        return "lei"
    return "outros"

REGRAS = {
    "melhoria": "Indicações: pedidos que o vereador manda à Prefeitura (roçada, vala, iluminação, asfalto, lombada...). A Prefeitura não é obrigada a atender.",
    "cobranca": "Requerimentos: perguntas e pedidos de informação a órgãos públicos ou empresas (Prefeitura, Sabesp, Estado...).",
    "homenagem": "Moções de aplauso ou pesar, títulos de cidadão, medalhas, nomes de rua e datas comemorativas, em qualquer tipo de documento.",
    "lei": "Projetos de lei, de lei complementar, de resolução, de decreto legislativo e emendas à Lei Orgânica que não são homenagem.",
    "outros": "O que não se encaixa acima, como moções de repúdio.",
}

# ---------- Passo 4: rua, bairro e tipo de servico ----------
# Temas (ordem importa: o primeiro que bater e o tema principal)
TEMAS = [
    ("Ruas de terra", r"nivelament|cascalh|encascalh|patrol|terraplan|motoniveladora"),
    ("Asfalto e buracos", r"asfalt|pavimenta|tapa.?buraco|buraco|recape|bloquete|paralelep"),
    ("Valas e drenagem", r"\bvala|bueiro|drenag|boca de lobo|desassore|alagament|galeria pluvial|canaleta"),
    ("Iluminação", r"ilumina|lampada|luminaria|poste|neoenergia|elektro|braco de luz"),
    ("Trânsito", r"lombada|redutor|faixa de pedestre|faixa elevada|sinaliza|placa|semaforo|transito|onibus|estacionamento|ciclovia|ciclofaixa|rotatoria|velocidade"),
    ("Limpeza e mato", r"rocad|rocagem|\bmato\b|capina|limpeza|entulho|lixo|cacamba|poda|arvore|galho|corte de grama"),
    ("Água e esgoto", r"\bagua\b|esgoto|sabesp|saneamento|abastecimento|hidrometro|vazamento"),
    ("Saúde", r"saude|\bubs\b|\bupa\b|hospital|medic|vacina|samu|ambulancia|dengue|enfermag|farmacia"),
    ("Educação", r"escola|creche|educa|aluno|ensino|transporte escolar|merenda"),
    ("Praças, esporte e lazer", r"praca|parque|quadra|esporte|lazer|academia|campo de futebol|playground|skate|ginasio"),
    ("Praia e turismo", r"praia|orla|turis|quiosque|guarda.?vida|temporada|calcadao"),
    ("Animais", r"animal|animais|\bcaes\b|\bcao\b|gatos?\b|castra|zoonose|\bpet\b"),
    ("Segurança", r"seguranca|guarda civil|\bgcm\b|policia|monitoramento|camera|videomonitor"),
    ("Calçadas e acessibilidade", r"calcada|guia|sarjeta|meio.?fio|acessibilidade|rampa"),
]
INFRA = {"Ruas de terra", "Asfalto e buracos", "Valas e drenagem", "Iluminação", "Trânsito", "Limpeza e mato", "Calçadas e acessibilidade", "Água e esgoto"}
def temas(ementa):
    e = sem_acento(re.sub(r"\s+", " ", ementa))
    return [nome for nome, rx in TEMAS if re.search(rx, e)]

PREFIXOS = re.compile(r"^(jardim|jd|balneario|bal|vila|parque|pq|conjunto habitacional|conj hab|conjunto|bairro|residencial|loteamento|chacaras?|estancia|nucleo|cidade)\s+")
def chave_bairro(b):
    k = chave(b)
    for _ in range(2):
        k = PREFIXOS.sub("", k)
    return " ".join(w[:-1] if w.endswith("s") and len(w) > 4 else w for w in k.split())

FIM = r"(?=,|;|\.|\s+(?:altura|alt\.|n[º°o\.]|numero|no bairro|bairro|localizad|em toda|esquina|entre|frente|em frente|ate|com a|com|proximo|nas proximidades|travessa da|trecho|no munic|neste|em itanha|conforme|bem como|visando|e na|e rua|e avenida|no jardim|no balneario|na vila|no parque|no conjunto)\b|$)"
RUA_RX = re.compile(r"\b(rua|avenida|av\.|estrada|travessa|alameda|pra[cç]a|viela|rodovia)\s+(.+?)" + FIM, re.I)
BAIRRO_RX = re.compile(r"(?:bairro|no|na|do|da)\s+((?:jardim|jd\.?|balne[aá]rio|vila|parque|conjunto habitacional|conj\.? hab\.?|ch[aá]caras?|cidade|recanto|n[uú]cleo|loteamento|residencial|estância|estancia|sitio|s[ií]tio)\s+[^,;.]+?)" + FIM.replace("|e na|e rua|e avenida|no jardim|no balneario|na vila|no parque|no conjunto", ""), re.I)
BAIRRO2_RX = re.compile(r"\bbairro\s+([^,;.]+?)" + FIM.replace("|no bairro|bairro", ""), re.I)

def limpa(s):
    s = re.sub(r"\s+", " ", s).strip(" -–—\"“”'")
    return s[:60]

ABREV = re.compile(r"\b(Ver|Vereador|Dr|Dra|Prof|Profa|Cel|Eng|Gov|Pres|Sen|Dep|Pe|Sto|Sta|Gal|Maj|Cap|Ten|Dna|Sr|Sra|Arq|Min)\.\s*")
def rua_bairro(ementa):
    ementa = ABREV.sub(lambda m: m.group(1) + " ", re.sub(r"\s+", " ", ementa))
    m = RUA_RX.search(ementa)
    rua = None
    if m:
        tipo = m.group(1).lower().replace("av.", "avenida").replace("praca", "praça")
        nome = limpa(m.group(2))
        if 2 < len(nome) and not re.match(r"(?i)^(do|da|de)\s*$", nome):
            rua = f"{tipo.capitalize()} {nome}"
    b = BAIRRO_RX.search(ementa) or BAIRRO2_RX.search(ementa)
    bairro = limpa(b.group(1)) if b else None
    if bairro:
        bairro = re.sub(r"(?i)^jd\.?\s", "Jardim ", bairro)
        bairro = re.sub(r"(?i)\s+(localizad\w*|neste|deste|em|no|na)$", "", bairro)
    return rua, bairro

def chave(s):
    return re.sub(r"[^a-z0-9 ]", "", sem_acento(s or "")).strip()

TITULOS = re.compile(r"\b(vereador|ver|doutor|doutora|dr|dra|professor|professora|prof|profa|governador|gov|coronel|cel|presidente|pres|engenheiro|eng|padre|pe|senador|deputado|prefeito)\b")
def chave_rua(rua):
    k = TITULOS.sub(" ", chave(rua))
    return re.sub(r"\s+", " ", re.sub(r"^(av|avenida)\b", "avenida", k)).strip()

def main():
    bruto = json.load(open(sys.argv[1], encoding="utf-8"))
    vers = bruto["vereadores"]
    idx_ver = {v["id"]: i for i, v in enumerate(vers)}

    # Os relatorios antigos (ate ~maio/2026) usam a numeracao interna do painel, nao a do portal.
    # Liga cada registro ao vereador pelo nome: precisa bater pelo menos 2 palavras (ou o apelido inteiro).
    def palavras(s): return {w for w in chave(s).split() if len(w) > 2 and w not in ("dos", "das", "de", "da", "do", "vereador")}
    alvo = {v["id"]: (palavras(v["nome"]), chave(v["apelido"])) for v in vers}
    def vid_de(r):
        if r["id"] in alvo:
            return r["id"]
        pn, cn = palavras(r["nome"]), chave(r["nome"])
        cands = [vid for vid, (ws, ap) in alvo.items() if len(pn & ws) >= 2 or cn == ap or (len(pn) == 1 and pn <= ws)]
        return cands[0] if len(cands) == 1 else None

    verif = {}
    caminho_verif = sys.argv[1].replace("dados.json", "verificacao.json")
    try:
        for r in json.load(open(caminho_verif, encoding="utf-8")):
            verif[r["pagina"]] = r
    except FileNotFoundError:
        pass

    # Presenca: por sessao, por vereador
    sess_out, pres = [], {v["id"]: collections.Counter() for v in vers}
    partido = {}
    sem_registro, divergencias = [], []
    for s in bruto["sessoes"]:
        if not s["chamadas"]:
            continue
        status = {}
        for c in s["chamadas"]:
            for r in c["registros"]:
                r["id"] = vid_de(r) or -r["id"]
                partido.setdefault(r["id"], r["partido"])
                st = r["status"]
                if st == "PRESENTE" or r["id"] not in status:
                    status[r["id"]] = st
                elif status[r["id"]] != "PRESENTE" and st != "AUSENTE":
                    status[r["id"]] = st
        data = s["chamadas"][0].get("data") or s.get("data_pagina")
        # Passo 5: se a ata da mesma sessao discorda do relatorio, nao conta nem presenca nem falta
        v = verif.get(s["id"])
        if v and v.get("ata") is not None:
            aus_rel = {vid for vid, st in status.items() if st != "PRESENTE"}
            for vid in set(v["ausentes_ata"]) ^ aus_rel:
                if vid in status:
                    divergencias.append({"vereador": vid, "data": data, "relatorio": status[vid],
                                         "ata": "AUSENTE" if vid in v["ausentes_ata"] else "PRESENTE",
                                         "arq": s["chamadas"][0]["arquivo"], "ata_titulo": v["ata"]})
                    status[vid] = "DIVERGENTE"
        for vid, st in status.items():
            if vid in pres:
                pres[vid][st] += 1
        titulo = s.get("sessao_real") or f"Sessão de {data}"
        sess_out.append({"id": s["id"], "t": titulo, "d": data,
                         "arq": [c["arquivo"] for c in s["chamadas"]],
                         "st": {str(k): v for k, v in status.items() if k in pres}})
    # Partido mais recente: a ultima sessao lida tem prioridade
    for s in reversed(bruto["sessoes"]):
        for c in s["chamadas"]:
            for r in c["registros"]:
                partido[r["id"]] = r["partido"]
        if s["chamadas"]:
            break

    props, por_rua = [], collections.defaultdict(list)
    nomes_bairro = collections.defaultdict(collections.Counter)
    for v in vers:
        for p in v["props"]:
            g = grupo(p["tipo"], p["ementa"])
            ts = temas(p["ementa"]) if g in ("melhoria", "cobranca", "lei") else []
            rua, bairro = rua_bairro(p["ementa"]) if g in ("melhoria", "cobranca") else (None, None)
            kb = chave_bairro(bairro) if bairro else None
            if kb:
                nomes_bairro[kb][bairro] += 1
            props.append([p["id"], v["id"], g, p["tipo"], p["num"], p["ano"], p["data"], p["ementa"], rua, bairro,
                          ts[0] if ts else None, kb])
            if g == "melhoria" and rua:
                for sv in (t for t in ts if t in INFRA):
                    por_rua[(chave_rua(rua), sv)].append(len(props) - 1)

    repetidos = []
    for (r, serv), itens in por_rua.items():
        if len(itens) < 2:
            continue
        itens.sort(key=lambda i: props[i][6])
        primeiro = props[itens[0]]
        kbs = collections.Counter(props[i][11] for i in itens if props[i][11])
        bairro = " / ".join(nomes_bairro[k].most_common(1)[0][0] for k, _ in kbs.most_common(2)) or None
        repetidos.append({"rua": primeiro[8], "bairro": bairro, "servico": serv, "n": len(itens), "itens": itens,
                          "autores": len({props[i][1] for i in itens})})
    repetidos.sort(key=lambda x: (-x["n"], x["rua"]))

    v_out = []
    for v in vers:
        c = pres[v["id"]]
        g = collections.Counter(p[2] for p in props if p[1] == v["id"])
        v_out.append({"id": v["id"], "apelido": re.sub(r"\b(De|Da|Do|Dos|Das|E)\b", lambda m: m.group(1).lower(), v["apelido"]), "nome": re.sub(r"\b(De|Da|Do|Dos|Das|E)\b", lambda m: m.group(1).lower(), re.sub(r"\s*\(.*", "", v["nome"]).title()),
                      "partido": partido.get(v["id"]), "foto": v.get("foto"), "cargo": v.get("cargo"), "pres": {k: n for k, n in c.items() if k != "DIVERGENTE"},
                      "diverg": c.get("DIVERGENTE", 0), "grupos": dict(g),
                      "total": sum(g.values())})
    v_out.sort(key=lambda x: x["apelido"])

    # Subsidio: Resolucao n 513/2024 prorroga a Resolucao n 490/2019 para 2025-2028.
    # Valor mensal informado no parecer do Projeto de Resolucao n 3/2024 (documento 79900, arquivo 90900).
    # Valores conferidos na folha de pagamento do Portal da Transparencia (coluna "Salario base", funcao VEREADOR):
    # jan-mar/2025 R$ 13.662; abr/2025-mar/2026 R$ 14.373; desde abr/2026 R$ 14.948 (a diferenca de abril veio na folha de maio).
    salario = {"mensal": 14948.00, "cadeiras": 10, "desde": "2025-01-01T00:00:00-03:00",
               "faixas": [["2025-01-01T00:00:00-03:00", 13662.00], ["2025-04-01T00:00:00-03:00", 14373.00],
                          ["2026-04-01T00:00:00-03:00", 14948.00]],
               "norma": "Resolução nº 513/2024, que mantém o subsídio da Resolução nº 490/2019, com os reajustes que aparecem na folha",
               "doc": 79900, "arq": 90900}
    # Bairros: nome mais usado para cada chave
    bairros = collections.Counter(p[11] for p in props if p[11])
    bairros_out = [{"k": k, "nome": nomes_bairro[k].most_common(1)[0][0], "n": n} for k, n in bairros.most_common()]
    # Desde quando cada vereador aparece nos relatorios (so mostra para quem tem menos sessoes)
    max_ses = max((sum(v["pres"].values()) + v["diverg"]) for v in v_out) if v_out else 0
    for v in v_out:
        if sum(v["pres"].values()) + v["diverg"] < max_ses:
            ds = [s_["d"] for s_ in sess_out if str(v["id"]) in s_["st"]]
            v["desde"] = min(ds, key=lambda d: d[-4:] + d[3:5] + d[:2]) if ds else None
    out = {"salario": salario, "bairros": bairros_out, "temas": [t for t, _ in TEMAS], "atualizado": bruto["coletado_em"], "anos": bruto["anos"], "regras": REGRAS,
           "vereadores": v_out, "props": props, "sessoes": sess_out, "divergencias": divergencias,
           "pres_de": min(x["d"][-4:]+x["d"][3:5]+x["d"][:2] for x in sess_out) if sess_out else None,
           "pres_ate": max(x["d"][-4:]+x["d"][3:5]+x["d"][:2] for x in sess_out) if sess_out else None,
           "repetidos": repetidos}
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # Resumo para conferencia
    print("vereadores:", len(v_out), "| proposituras:", len(props), "| sessoes com presenca:", len(sess_out),
          "| divergencias:", divergencias, "| ruas com pedido repetido:", len(repetidos))
    for v in v_out:
        print(f"  {v['apelido']:<22} {v['partido'] or '?':<13} pres={v['pres']} grupos={v['grupos']}")
    com_rua = sum(1 for p in props if p[2] == "melhoria" and p[8])
    tot_mel = sum(1 for p in props if p[2] == "melhoria")
    print(f"indicacoes com rua identificada: {com_rua}/{tot_mel}")

if __name__ == "__main__":
    main()
