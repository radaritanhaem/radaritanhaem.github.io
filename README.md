# Radar Itanhaém

**Site:** https://radaritanhaem.github.io/

Raio-X da Câmara Municipal de Itanhaém-SP com dados oficiais: propostas de cada vereador, presença nas sessões, problemas que voltam nos bairros, salários da Câmara (por cargo, sem nomes) e licitações.

## O que tem aqui

| Pasta | O que é |
|---|---|
| `site/` | O site (uma página só) e os dados prontos (`dados-site.json`) |
| `coletor/` | O robô que busca os dados oficiais |
| `dados/` | Os dados brutos baixados (para quem quiser conferir) |
| `.github/workflows/atualizar.yml` | Agenda do robô: roda toda madrugada às 5h |

## Fontes (somente oficiais)

- Portal da Câmara (SISCAM): vereadores, propostas, relatórios de presença e atas. https://www.itanhaem.sp.leg.br
- Portal da Transparência da Câmara: folha de pagamento. https://transparencia.itanhaem.sp.leg.br
- Página de licitações da Câmara e o PNCP (Portal Nacional de Contratações Públicas): https://pncp.gov.br

## Como colocar no ar (uma vez só)

1. Crie uma conta em https://github.com (grátis), se ainda não tiver.
2. Crie um repositório **público** chamado `radar-itanhaem` (botão **New**). Não marque nenhuma opção de README.
3. Envie esta pasta para o repositório. Pelo site do GitHub: **Add file → Upload files**, arraste todas as pastas e arquivos e clique em **Commit changes**.
4. No repositório, vá em **Settings → Pages** e, em **Source**, escolha **GitHub Actions**.
5. Vá em **Actions**, clique em **Atualizar o Radar** e em **Run workflow**. A primeira coleta leva cerca de 1 hora.
6. O endereço do site aparece em **Settings → Pages**, no formato `https://SEU-USUARIO.github.io/radar-itanhaem/`.

Depois disso o robô roda sozinho todo dia. Se a coleta vier incompleta ou estranha, ele **não publica** e o site continua com a última versão boa. Para ver o que aconteceu, abra a aba **Actions**: uma bolinha vermelha mostra o motivo.

## Rodar no próprio computador

```
pip install pillow playwright
python -m playwright install chromium
python coletor/coletar.py dados 2025 2026
python coletor/verificar.py dados/dados.json dados/verificacao.json
python coletor/licitacoes.py dados/licitacoes.json 2025
python coletor/folha.py dados/folha.json
python coletor/processar.py dados/dados.json site/dados-site.json
python coletor/processar_extra.py dados/folha.json dados/licitacoes.json site/dados-site.json
```
Precisa também do `pdftotext` (pacote poppler).

## Regras do projeto

1. Só dados oficiais, sempre com link para a fonte.
2. A mesma regra vale para todos os vereadores.
3. Estimativa é marcada como estimativa.
4. Na folha de pagamento não aparecem nomes nem matrículas, só o cargo.
5. Dado que falta não é falta: ausência de registro não vira acusação.
6. Porta aberta para correções: pela aba **Issues** deste repositório.
