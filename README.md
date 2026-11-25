# Transparência Itanhaém

**Site de teste:** https://radaritanhaem.github.io/ · **Endereço final:** https://www.transparenciaitanhaem.com.br (depois da troca do domínio)

Portal de notícias de Itanhaém-SP com fiscalização do poder público:

- **Notícias** da cidade (`/noticias`, cada matéria em `/noticia/<endereço>`, os mesmos endereços do portal antigo)
- **Raio-X da Câmara** (`/camara/`): propostas, presença, salários por cargo e licitações, só com dados oficiais
- **Raio-X da Prefeitura** (`/prefeitura/`): gasto por secretaria e secretários (em construção)
- Documentos, podcasts, vídeos, eventos, vagas e guia comercial

## Pastas

| Pasta | O que é |
|---|---|
| `conteudo/` | As notícias e demais publicações, um arquivo `.md` por publicação |
| `site/` | O que vai para o ar. `site/camara/` é o Raio-X da Câmara; `site/uploads/` são fotos e PDFs |
| `coletor/` | Os programas: robô de dados (`coletar`, `folha`, `licitacoes`...) e o gerador do portal (`gerar_site.py`) |
| `dados/` | Dados brutos baixados das fontes oficiais |
| `.pages.yml` | Configuração do painel de publicação |

As páginas de notícias em `site/` são geradas a cada publicação e não ficam guardadas no repositório.

## Publicar uma notícia (painel grátis)

1. Abra https://app.pagescms.org e entre com a conta do GitHub.
2. Escolha o repositório **radaritanhaem/radaritanhaem.github.io**.
3. Menu **Notícias → Add an entry**: título, categoria, data, foto de capa e texto. Clique em **Save**.
4. Em cerca de 1 minuto a notícia está no ar.

Para vídeos, envie para o canal do YouTube e cole o link do vídeo sozinho numa linha do texto: ele vira o player.

## Robô diário

Todo dia às 5h (Brasília) o robô busca os dados da Câmara, confere e publica. Se algo vier estranho, ele **não publica** e o site fica com a última versão boa. Veja na aba **Actions**.

## Pendências antes de desligar o portal antigo

- [x] **Vídeos enviados ao portal antigo**: os 19 vídeos foram comprimidos e estão em `site/uploads/medias/` (mesmos endereços de antes). Vídeos novos: pelo YouTube.
- [ ] **E-mail @transparenciaitanhaem.com.br**: se for usado, configurar antes da troca do domínio.
- [ ] **Troca do domínio**: em registro.br, apontar `transparenciaitanhaem.com.br` para o GitHub Pages e configurar o domínio em Settings → Pages.

## Fontes (somente oficiais)

- Câmara: https://www.itanhaem.sp.leg.br e https://transparencia.itanhaem.sp.leg.br
- Licitações: página da Câmara e PNCP (https://pncp.gov.br)
- Prefeitura: https://dadosabertos.itanhaem.sp.gov.br e TCE-SP (https://transparencia.tce.sp.gov.br)

## Regras

1. Só dados oficiais, sempre com link para a fonte.
2. A mesma regra vale para todos.
3. Estimativa é marcada como estimativa.
4. Na folha de pagamento não aparecem nomes nem matrículas, só o cargo.
5. Dado que falta não é falta: ausência de registro não vira acusação.
6. Correções pela aba **Issues** deste repositório.
