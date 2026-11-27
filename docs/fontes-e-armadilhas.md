# Fontes oficiais e armadilhas já resolvidas

Tudo o que foi descoberto (às vezes do jeito difícil) sobre cada fonte. Antes de alterar um coletor, leia a seção correspondente.

## 1. Câmara Municipal — SISCAM (`https://www.itanhaem.sp.leg.br`)

Sistema SISCAM (Sino Informática), não é SAPL.

| Dado | Endereço |
|---|---|
| Vereadores em exercício | `/siscam/Documentos?handler=autor&tipoAutorId=1&todos=true&pagina={n}&texto=` (JSON; `"secondary": false` = atual) |
| Propostas de um vereador (CSV oficial) | `/siscam/Documentos?Pesquisa=Avancada&GrupoId=7&TipoAutorId=1&AutorId={id}&TipoIniciativaId=1&Ano={ano}&Ordenacao=4&Export=Csv` (sem coluna de autor: consultar vereador por vereador; data vem MM/DD/AAAA) |
| Sessões do ano | `/siscam/Reunioes?Pesquisa=Avancada&TipoId=1&Ano={ano}&ItemsPerPage=100&Ordenacao=4` (conferir com o texto "N registros") |
| Página da sessão | `/Siscam/Reunioes/Details?id={id}` |
| Arquivo (PDF) | `/Siscam/Documentos?handler=Arquivo&id={id}` |
| Documento | `/Siscam/Documentos/Details?id={id}` |
| Ficha do vereador | `/Vereadores/Details?id={id}` |
| Fotos | `/vereadores?tab=vereadores` (img `/Vereadores?id=N&handler=ImagemVereadores` antes do link Details) |
| Mesa Diretora | `/vereadores?tab=mesa` (cargo aparece antes do link Details) |
| Licitações da Câmara | `/Licitacao?CurrentPage={n}` (10 por página; valores e vencedores vêm do PNCP) |

**Armadilhas**
- **Relatórios de presença** ("PRESENÇA 1", PDF assinado) só existem a partir de **fevereiro de 2026** e ficam anexados na página da **sessão seguinte**, junto com a ata. O título real da sessão é lido de dentro do PDF (`verificar.py`).
- Relatórios do início de 2026 usam **IDs internos do painel** (ex.: Fernando = 7, Willian = 16, Severino Bento Gomes = 13, ex-vereador) e nomes em caixa mista ("Alexandre Firmino Alves"); `processar.py` (`vid_de`) liga por nome.
- **`pdftotext` muda de programa para programa.** O computador do projeto tem **xpdf 4.06**; o GitHub (Ubuntu) tem **poppler**. No modo `-raw` a ORDEM do texto vem do próprio PDF (partido, status, legislatura, nome, horário, id), mas as quebras de linha mudam. O leitor (`coletar.py: ler_presenca`) junta todo o texto com espaços antes de procurar — não volte a depender de `\n`. O modo `-layout` desalinha as linhas (já causou erro: pareceu que um vereador faltou). Saída do Windows tem `\r`.
- Sem o leitor certo, a presença **sumiu do site** em 25–26/11/2026; por isso `validar.py` bloqueia a publicação se a presença vier vazia ou cair.
- Conferência com as atas: as atas trazem "(... AUSENTE ...)" no texto. Hoje só **uma** divergência: 66ª sessão (14/09/2026), Professor Fernando — relatório diz PRESENTE, ata diz AUSENTE. Fica fora da conta e é mostrada no crachá.
- Votos individuais **não são publicados** (só "aprovado com N votos"). O relatório de presença não traz justificativa de ausência — o site diz "ausência registrada", nunca "falta".
- Câmara aceita robô dos EUA (GitHub) normalmente.

## 2. Portal da Transparência da Câmara (GCASP) — `https://transparencia.itanhaem.sp.leg.br`

Sistema **GCASP (GeneXus)**: páginas com postback e sessão no servidor; só funciona com navegador (Playwright). A API `apitransparencia.itanhaem.sp.leg.br` (`/consulta-contratos` etc.) respondeu **vazia**.

- **Folha** (`/filtros-recursoshumanos`): escolher mês no combo `#W0012COMBO_MESContainer_btnGroupDrop` (itens `a.ExtendedComboLevel0`), clicar "Confirmar", ler a grade (5 linhas por página, botão `li.next a`, texto "Página X de Y"). Colunas (índice da célula): 1 matrícula, 2 nome (**nunca guardar**), 3 organograma, 7 função, 9 vínculo, 13 salário base, 14 descontos, 15 vantagens, 16 férias, 17 aposentadoria, 18 bolsa estágio, 19 pensão, 20 líquido.
- **Bruto** = base + vantagens + férias + aposentadoria + pensão (a bolsa de estágio já está dentro de "vantagens"). Em ~20 de 781 linhas (2 cargos de auxiliar) a conta do próprio portal não fecha; mostramos como publicado.
- **Subsídio do vereador** (conferido na folha, função VEREADOR): R$ 13.662 (jan–mar/2025), R$ 14.373 (abr/2025–mar/2026), R$ 14.948 (desde abr/2026; diferença de abril paga em maio). Vereador não recebe 13º. Esses valores estão fixos em `processar.py` (`salario.faixas`) — **atualizar quando houver reajuste**.

## 3. PNCP — `https://pncp.gov.br/api`

- Compra: `/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}` (estimado, homologado, situação). Itens: `/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens`. Vencedor: `.../itens/{n}/resultados`.
- `/consulta/v1/contratos` e `/consulta/v1/contratacoes/publicacao` estão **instáveis** (erro 500 / muito lentos). Para a Prefeitura não usamos o PNCP.
- CNPJ da Câmara: 54.353.586/0001-05.

## 4. Prefeitura — Portal de Dados Abertos (GCASP) — `https://dadosabertos.itanhaem.sp.gov.br`

Mesmo sistema GCASP. Órgãos no combo `#vORGAO_MPAGE`: 1 Câmara, 2 Prefeitura, 3 ITAPREV.

- **Despesas pagas** (`/filtros-despesasorcamentarias`): datas `#W0012vDATAINICIAL/#W0012vDATAFINAL`, unidade "GERAL", `#W0012vCONSIDERAR` = 4 (despesa paga), botão `#W0012BTNENTER`. Resultado em `/resultado-despesaorcamentaria-posicao-paga` com o **total no rodapé** (texto antes de "Ant").
- **Exportar CSV:** clicar em "Exportar Dados" (`#DDO_ACTIONGROUPEXPORTContainer_btnGroupDrop`) → "CSV" (prepara o arquivo no servidor) e só então baixar `GET /wpdespesaorcamentariapagaexportcsv.aspx` (mesma sessão). Sem o clique o arquivo vem vazio (~21 bytes). CSV em UTF-8, separador `;`, valores com ponto decimal, datas `ddmmaaaa` **sem zero à esquerda** (usar `zfill(8)`), processo sem barra (`137592026` = 13759/2026; últimos 4 dígitos = ano).
- O filtro de data é pela **data de emissão do empenho**: entram só despesas criadas no ano; **restos a pagar** de anos anteriores ficam de fora (por isso janeiro é baixo). Somamos pela **data de pagamento**.
- "PREFEITURA MUNICIPAL DE ITANHAEM" (CNPJ 46.578.498/0001-75) como fornecedor = **folha de pagamento**; "INSTITUTO DE PREVIDENCIA..." (CNPJ 08.424.027/0001-13) = **ITAPREV**.
- Conferido: soma do CSV = total do portal (ex.: R$ 555.581.537,11 em 2026) e = TCE-SP mês a mês (jan–set, centavo por centavo).
- **Compras e licitações** (`/filtros-compraselicitacoes`): resultado em `/resultado-compraselicitacoes` (10 por página); CSV em `GET /wpcompraslicitacoeshomologadasexportcsv.aspx` após clicar CSV. Alguns campos têm **quebra de linha dentro do texto**: juntar linhas até ter 15 colunas (`prefeitura.py: ler_compras`). O campo **Objeto vem cortado em ~90 letras pelo próprio portal**. Não há coluna de vencedor: ligamos compra ↔ pagamentos pelo **número do processo** (`por_processo`); o valor pago bateu em 161 de 161 compras.
- **Secretários:** páginas `https://www.itanhaem.sp.gov.br/secretaria-.../` (lista em `/secretarias/`), linha seguinte a "SECRETÁRIO(A)" (Procuradoria: "PROCURADOR GERAL DO MUNICÍPIO"). Governo Municipal está com o campo vazio; Serviços Públicos e Zeladoria não tem página — o site diz "Não informado no site da Prefeitura".
- A API `apitransparencia.itanhaem.sp.gov.br` não tem despesas.

## 5. ITAPREV (Itanhaém Prev) — `https://transparenciaonline.gcaspp.com`

- Só abre depois de escolher o órgão 3 no portal da Prefeitura (ele **redireciona** e guarda na sessão). `prefeitura.py: entrar()` faz isso; use `--itaprev` nos comandos.
- Mesmas buscas e exportações da Prefeitura (despesas, compras). Na busca de despesas o combo de unidade pode não ter "GERAL" (o código tolera).
- **Folha** (`/filtros-recursoshumanos`): ~1.140 pessoas, 229 páginas; colunas diferentes da Câmara: 13 referência salarial, 14 vantagens, 15 descontos, 16 líquido. Estagiários vêm com zero (bolsa em outra coluna) — ficam fora das médias.
- Organogramas: APOSENTADOS / PENSIONISTAS PLANO FINANCEIRO ou PREVIDENCIÁRIO, SERVIDOR ..., ESTAGIÁRIOS.

## 6. TCE-SP — API de transparência (`https://transparencia.tce.sp.gov.br/api/json`)

- `/municipios`, `/despesas/itanhaem/{ano}/{mes}`, `/receitas/itanhaem/{ano}/{mes}` (arquivos grandes, ~1,4 MB; às vezes dá timeout — repetir com pausa).
- Despesas: campos `orgao`, `evento` (**"Valor Pago"**, "Empenhado", "Valor Liquidado", "Anulação"), `id_fornecedor` ("CNPJ - PESSOA JURÍDICA - 00.000..."), `nm_fornecedor`, `vl_despesa` ("1.234,56"). Receitas: `ds_alinea`, `ds_subalinea`, `vl_arrecadacao`.
- **Atraso de ~2 meses**: meses recentes vêm vazios ("TCE ainda não publicou").
- Não tem divisão por secretaria (só por órgão) — serve para **conferir**, não para detalhar.
- Repasses Prefeitura/Câmara → ITAPREV: identificar pelo **CNPJ 08424027000113** no `id_fornecedor` (o nome muda).

## 7. Portal antigo de notícias (migração, já concluída)

- Era um sistema de portal de notícias pago (~R$ 53/mês) sobre HostGator/cPanel com Cloudflare de terceiros. Notícias em `/noticia/<slug>`, conteúdo em `div#content.post-content`, dados em JSON-LD (`datePublished`). Créditos e tags no fim do texto foram separados.
- 19 vídeos enviados (837 MB) foram comprimidos com ffmpeg (854 px, CRF 30, máx. 450 kbps, AAC 64k mono, faststart) para 214 MB e ficam em `site/uploads/medias/` nos mesmos caminhos. PNGs viraram JPG ≤1200 px.
- Não migrados: web stories, enquete, classificados/cupons/câmeras (vazios), futebol (por decisão).

## 8. Ambiente e ferramentas

- Windows com caminhos longos: prefixo `\\?\` nos programas; `subst R:` no terminal; `servidor_local.py` traduz caminhos.
- Sem PIL no computador local: fotos reduzidas com ffmpeg (`scale=480:-2`). No GitHub o PIL existe e `coletar.py` reduz sozinho. **Não publique fotos de 2–3 MB** (aconteceu uma vez).
- Playwright: instalação local foi bloqueada pela política de permissões; rodar só no GitHub ou usar o navegador do app para testes.
- Baixar binários de fora no robô (ex.: xpdf no GitHub) também foi bloqueado pela política — por isso o leitor de PDF foi tornado independente do programa.
- Python com `-I` ignora `PYTHONIOENCODING`; use `-X utf8`.
- Edições via heredoc em bash podem transformar `\b` em caractere de controle — conferir regex depois.

## Entidades sem fins lucrativos (Prefeitura)

- `prefeitura.py` guarda em `prefeitura_despesas.json` o campo `pj`: total pago a **cada** CNPJ (com secretaria, tipo de despesa, modalidade e objeto).
- `entidades.py` confere a natureza jurídica de cada CNPJ em https://minhareceita.org (reserva: BrasilAPI, que limita após ~90 consultas seguidas). Fica o grupo 3 (sem fins lucrativos), menos cartórios (3034) e condomínios (3085). O cache `dados/cnpj_receita.json` guarda só código, descrição e razão social.
- **Matriz e filial** (mesma raiz de 8 dígitos) são somadas: a Prefeitura estornou R$ 3,4 mi da filial da Vida Livre e pagou na matriz em set/2026.
- O nome na Prefeitura pode ser outro: "Associação Beneficente de Amparo e Solidariedade" é o **Instituto Anglicano de Itanhaém** na Receita. O cartão mostra os dois.
- Receber ≠ doação: muitos pagamentos são aluguel (Santa Casa, Mitra Diocesana) ou serviço por pregão.
- Câmara (TCE-SP, jan–set/2026): só o CIEE (estágio, R$ 5.955,62).

## Alertas do TCE-SP

- Comunicados SDG "ALERTAS de que trata o parágrafo 1º do artigo 59 da LRF" (busca em /legislacao?termo=ALERTAS artigo 59&f[0]=tipo:18). Em 2026: nº 26, 36, 42 e 55.
- Ler com `pdftotext -raw` (o `-layout` desalinha as linhas das tabelas!). Seções: inciso II (pessoal), incisos I/III/V, "municípios que deixaram de enviar o balancete", "1. Câmaras", "2. Entidades da administração indireta". Linha fora de seção conhecida vai para `a_conferir` e não é publicada.
- O título de seção do comunicado 36/2026 diz "2º BIMESTRE 2025" por erro do TCE; o site usa o texto "relativos ao ..." da página do comunicado.
- Visor (painel.tce.sp.gov.br, Pentaho): abrir `.../visor.wcdf/generatedContent?userid=anony&password=zero` para pegar o cookie e então POST em `/pentaho/plugin/cda/api/doQuery` (`dataAccessId=visorDS`, `parampAno`, `parampEntidade=PREFEITURA MUNICIPAL`, `parampAssunto`). Só dá contagem. Existe contagem escondida para "CÂMARA MUNICIPAL" (3 em 2026) sem detalhe; não publicada.
- O site do ITAPREV (gcaspp.com) passou a ter verificação anti-robô da Cloudflare em 27/11/2026: pagamentos, compras e folha do instituto só atualizam pelo navegador do app. Não contornar.
