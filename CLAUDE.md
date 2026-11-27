# Transparência Itanhaém — guia do projeto (leia primeiro)

Portal de notícias + fiscalização do poder público de Itanhaém-SP, no ar em **https://www.transparenciaitanhaem.com.br**.
Dono: Transparência Itanhaém (contato público: movimentotransparenciaitanhaem@gmail.com). Idioma do projeto, do site e das conversas: **português do Brasil, linguagem simples**.

Documentos complementares:
- `docs/fontes-e-armadilhas.md` — cada fonte oficial, como é lida e os problemas já resolvidos. **Leia antes de mexer em qualquer coletor.**
- `docs/historico-e-proximos-passos.md` — decisões tomadas, linha do tempo e pendências.
- `README.md` — versão pública e curta (aparece no GitHub).

## O que o site tem

| Endereço | O que é | Gerado por |
|---|---|---|
| `/` | Página inicial: manchetes + blocos Câmara, Prefeitura e Previdência | `coletor/gerar_site.py` |
| `/noticia/<endereco>` e `/noticias/<categoria>` | 69 notícias migradas do portal antigo (mesmos endereços) + novas do painel | `gerar_site.py` a partir de `conteudo/` |
| `/camara/` | Raio-X da Câmara: propostas, bairros, problemas que voltam, presença, salários por cargo, licitações | página própria `site/camara/index.html` + `site/camara/dados-site.json` |
| `/prefeitura/` | Raio-X da Prefeitura: gasto pago por secretaria, mês a mês, secretários | `gerar_site.py` (`pagina_prefeitura`) |
| `/prefeitura/compras/` | Compras e licitações homologadas, valor pago e empresas que receberam | `gerar_site.py` (`pagina_compras`) |
| `/prefeitura/entidades/` | Associações e entidades sem fins lucrativos que receberam (valor pago), achadas pela natureza jurídica do CNPJ na Receita | `entidades.py` + `gerar_site.py` (`pagina_entidades`) |
| Quadro vermelho "Alerta do TCE-SP" | Em `/prefeitura/`, `/itaprev/` e `/camara/` (entre `<!--alertas-tce-->`), só quando há alerta | `tce_alertas.py` + `gerar_site.py` (`bloco_alertas`) |
| `/itaprev/` | Raio-X da Previdência (ITAPREV): entra x sai, repasses, benefícios, equipe, compras | `gerar_site.py` (`pagina_itaprev`) |
| `/documentos`, `/podcasts`, `/videos`, `/guia-comercial`, `/eventos`, `/vagas` | Conteúdo migrado do portal antigo | `gerar_site.py` |
| `rss.xml`, `sitemap.xml`, `404.html` | — | `gerar_site.py` |

## Regras de ouro (não negociáveis)

1. **Só dados oficiais**, sempre com link para a fonte. Nada de estimativa sem dizer que é estimativa.
2. **Privacidade:** folhas de pagamento mostram **cargo, nunca nome nem matrícula** (a matrícula da folha da Câmara é trocada por número interno sorteado). Pagamentos a **pessoa física** aparecem como "Pessoas físicas (nomes não exibidos)". Empresas (CNPJ) podem aparecer.
3. **Mesma regra para todos** os vereadores/órgãos. Sem notas, rankings de "melhor/pior" ou acusações. Dado ausente não é falta.
4. **Conferir antes de publicar:** toda soma é comparada com o total do próprio portal oficial e, quando possível, com o TCE-SP. O robô não publica se algo cair ou vier vazio (`coletor/validar.py`).
5. **Porta aberta para correções:** aba Issues do repositório.

## Estrutura do repositório

```
conteudo/            notícias e publicações (.md com cabeçalho YAML + texto HTML/Markdown)
  noticias/ edicoes/ podcasts/ videos/ eventos/ vagas/ guia/
coletor/             programas (Python 3.12)
  coletar.py         Câmara (SISCAM): vereadores, fotos, Mesa, propostas, sessões e relatórios de presença (PDF)
  verificar.py       confere cada relatório de presença com a ata da sessão
  processar.py       monta site/camara/dados-site.json (grupos, temas, bairros, ruas repetidas, presença, salário)
  processar_extra.py acrescenta folha da Câmara (por cargo) e licitações da Câmara ao dados-site.json
  folha.py           folha da Câmara (Portal da Transparência da Câmara, Playwright)
  licitacoes.py      licitações da Câmara (página da Câmara + API do PNCP)
  prefeitura.py      Prefeitura e ITAPREV (portal GCASP, Playwright): despesas pagas, compras, secretários, conferência TCE
  itaprev.py         ITAPREV: entra x sai e repasses (API TCE-SP) + folha do instituto (Playwright)
  entidades.py       entidades sem fins lucrativos pagas pela Prefeitura (cadastro da Receita via minhareceita.org; cache em dados/cnpj_receita.json)
  tce_alertas.py     alertas do TCE-SP: comunicados SDG do art. 59 da LRF (PDF, pdftotext -raw) + contagem do painel Visor
  validar.py         trava de segurança antes de publicar
  gerar_site.py      gera todas as páginas do portal a partir de conteudo/ e dados/
  migrar_portal.py   (uso único, já feito) copiou o portal antigo
  servidor_local.py  servidor para ver o site no computador (igual ao GitHub Pages)
dados/               dados brutos coletados (JSON) — o robô atualiza; dados/registro/ guarda logs das coletas
site/                o que vai para o ar (GitHub Pages). Páginas geradas estão no .gitignore
  assets/estilo.css, assets/site.js   estilo e scripts do portal
  camara/            Raio-X da Câmara (index.html escrito à mão, dados-site.json, fotos/)
  uploads/           fotos, PDFs e vídeos migrados (mesmos caminhos do portal antigo)
  marca/             logo e ícone do Transparência Itanhaém
.github/workflows/atualizar.yml   robô diário + publicação
.pages.yml           configuração do painel de publicação (Pages CMS)
```

## Comandos

Requisitos locais: Python 3.12, `pdftotext` (no computador do projeto é o **xpdf 4.06**), `ffmpeg` (para fotos/vídeos), Node (só para `node --check`). Playwright **não** está instalado no computador local (a instalação foi bloqueada); as coletas com navegador rodam no GitHub ou são feitas pelo navegador do app.

```bash
# Câmara
python coletor/coletar.py dados 2025 2026
python coletor/verificar.py dados/dados.json dados/verificacao.json
python coletor/licitacoes.py dados/licitacoes.json 2025
python coletor/processar.py dados/dados.json site/camara/dados-site.json
python coletor/processar_extra.py dados/folha.json dados/licitacoes.json site/camara/dados-site.json

# Prefeitura (precisa de Playwright) — acrescente --itaprev para o instituto de previdência
python coletor/prefeitura.py despesas /tmp/p.json && python coletor/prefeitura.py aceitar /tmp/p.json dados/prefeitura_despesas.json
python coletor/prefeitura.py compras /tmp/c.json && python coletor/prefeitura.py aceitar-compras /tmp/c.json dados/prefeitura_compras.json
python coletor/prefeitura.py secretarios dados/prefeitura_secretarios.json
python coletor/prefeitura.py conferir dados/prefeitura_despesas.json dados/prefeitura_conferencia.json

# ITAPREV
python coletor/itaprev.py tce dados/itaprev_tce.json          # sem Playwright
python coletor/itaprev.py folha dados/itaprev_folha.json      # Playwright

# Entidades sem fins lucrativos e alertas do TCE (sem Playwright)
python coletor/entidades.py dados/prefeitura_despesas.json dados/prefeitura_entidades.json
python coletor/tce_alertas.py dados/tce_alertas.json

# Conferir e gerar o portal
python coletor/validar.py <dados-site anterior> site/camara/dados-site.json
python coletor/gerar_site.py

# Ver no computador (http://localhost:8791)
python coletor/servidor_local.py 8791
```

**Windows:** a pasta do projeto pode ter caminho longo (>260 letras) e quebrar leitura de arquivos. Os programas usam o prefixo `\\?\`; no terminal, crie um atalho: `subst R: "<pasta do projeto>"` e trabalhe em `R:\`.

## Robô diário (`.github/workflows/atualizar.yml`)

- Roda às **05:00 de Brasília** (cron `0 8 * * *`), pelo botão **Run workflow** e a cada push que mexe em `site/`, `conteudo/` ou `coletor/gerar_site.py` (nesse caso só refaz as páginas e publica).
- Ordem: Câmara → licitações → folha da Câmara → Prefeitura (despesas, compras, secretários, TCE) → ITAPREV (TCE, despesas, compras, folha) → `processar*.py` → `validar.py` → `gerar_site.py` → commit "Dados de dd/mm/aaaa" → deploy no GitHub Pages.
- Passos com navegador (folha, Prefeitura, ITAPREV) são `continue-on-error`: se falharem, o site fica com os últimos dados bons e o motivo fica em `dados/registro/*.txt` (e print/HTML da página em caso de falha).
- **Quando der vermelho:** veja a aba Actions; o relatório do passo está em `dados/registro/`. Nunca use "Re-run jobs" de uma execução antiga depois de corrigir código (ela roda o código antigo) — use "Run workflow".
- A API pública do GitHub tem limite de 60 consultas/hora sem login; não fique consultando o andamento em loop rápido.

## Publicação de notícias (painel)

Pages CMS (https://app.pagescms.org), entrando com a conta GitHub `oprodutorjappa`, repositório `radaritanhaem/radaritanhaem.github.io`. Coleções: **Notícias** (`conteudo/noticias`) e **Documentos (PDF)** (`conteudo/edicoes`). Editor em HTML (as notícias migradas são HTML). Datas no formato `aaaa-mm-ddThh:mm` (horário de Brasília; o gerador acrescenta `-03:00`). Fotos vão para `site/uploads/painel/`. Vídeos novos: YouTube (link sozinho numa linha vira player).

## Hospedagem e domínio

- GitHub: organização **radaritanhaem**, repositório **radaritanhaem.github.io** (site em GitHub Pages, fonte = GitHub Actions, domínio próprio `www.transparenciaitanhaem.com.br`).
- DNS: conta **Cloudflare do projeto** (plano Free), servidores `grannbo.ns.cloudflare.com` e `viddy.ns.cloudflare.com`. Registros: 4 × A `@` → 185.199.108.153 / .109 / .110 / .111 e CNAME `www` → `radaritanhaem.github.io`, **todos "DNS only" (nuvem cinza)** — com proxy laranja o HTTPS do GitHub não funciona.
- Domínio registrado no registro.br via revenda **HostGator (Newfold)**; os servidores DNS se trocam no painel da HostGator ("Configurar domínio" → "Outra plataforma de hospedagem"). Renovação anual pela HostGator (vencimento informado: maio/junho de 2027). O domínio **não tem e-mail**.

## Visual

Fontes Archivo (títulos) e Public Sans (texto); tokens de cor em `:root` com modo escuro; azul `#0a63b8`, vermelho de alerta, verde ok; logo do Transparência Itanhaém (detetive com lupa). Gráficos: paleta categórica validada (6 cores `--g1`…`--g6`, ver `site/assets/estilo.css`), sempre com legenda e valores escritos. **Teste sempre no celular** (375 px): sem rolagem lateral, barras visíveis.
