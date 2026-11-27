# Histórico, decisões e próximos passos

## Linha do tempo

| Data | O que aconteceu |
|---|---|
| 24/11/2026 | Radar Itanhaém criado a partir do manual "Como criar o Radar da sua cidade" (modelo: radarptlandia.org): propostas por vereador, bairros, ruas com pedido repetido, presença com conferência nas atas, fotos, contador de salário ao vivo. |
| 24/11/2026 | Folha da Câmara por cargo (sem nomes) e licitações da Câmara (PNCP). Descoberto que o subsídio real é R$ 14.948 (não R$ 13.662). |
| 24/11/2026 | Publicado no GitHub Pages; organização `radaritanhaem` criada (endereço sem o nome pessoal do dono); logo do Transparência Itanhaém. |
| 25/11/2026 | Unificação: o portal de notícias pago (transparenciaitanhaem.com.br) migrado para o mesmo site; "Radar" deixou de ser nome; Câmara virou `/camara/`. Painel Pages CMS configurado. Raio-X da Prefeitura (gasto por secretaria, secretários, conferência TCE). |
| 25/11/2026 | Robô completo rodando no GitHub (correções: ordem do apelido, espera por elementos em vez de "rede quieta", relatórios em `dados/registro/`, salvar sem conflito). Vídeos comprimidos. Domínio trocado para o GitHub (DNS na Cloudflare do projeto). |
| 25/11/2026 | Compras e licitações da Prefeitura (`/prefeitura/compras/`), ligadas aos pagamentos pelo número do processo. |
| 26/11/2026 | Presença tinha sumido (pdftotext diferente no GitHub): leitor corrigido e trava no `validar.py`. Gráfico mensal da Prefeitura corrigido no celular. |
| 26/11/2026 | Raio-X da Previdência (ITAPREV) em `/itaprev/`. Documentação do projeto (este arquivo, `CLAUDE.md`, `docs/fontes-e-armadilhas.md`). |

## Decisões importantes (e por quê)

- **Um site só** no domínio do portal, para divulgar um endereço e cancelar a mensalidade do portal antigo.
- **GitHub Pages + robô no GitHub Actions**: grátis, sem servidor para manter; o histórico de dados fica versionado.
- **Sem nomes de servidores**, só cargos (pedido do dono). Pessoa física que recebe pagamento: nome oculto.
- **Presença**: "ausência registrada", nunca "falta" (relatório não tem justificativa). Só desde fev/2026 (antes só há ata em texto).
- **Compras da Prefeitura**: "quem recebeu" vem dos pagamentos ligados ao processo (o portal não informa vencedor; PNCP instável).
- **Vídeos**: comprimidos e hospedados no próprio site (o dono não quis subir no YouTube; muitos são trechos de TV, que o YouTube poderia bloquear). Vídeos novos devem ir para o YouTube.
- **Previdência**: tema sensível (Operação Buraco Negro do MP). A página mostra só números oficiais e linka a notícia, sem acusações.
- **Domínio**: em vez de pedir ao fornecedor do portal antigo, o dono criou Cloudflare própria e trocou os DNS na HostGator.

## Pendências (verificar na próxima conversa)

- [ ] Confirmar que o robô das 5h rodou verde **com as partes novas** (compras da Prefeitura, ITAPREV, presença com o leitor novo). Ver `dados/registro/*.txt` e a aba Actions.
- [ ] Marcar **"Enforce HTTPS"** em Settings → Pages (se ainda não estiver marcado).
- [ ] Cancelar o plano do portal antigo **só depois de 1–2 semanas** com tudo funcionando (a partir de 25/11/2026). **Não cancelar o domínio** (renovação anual na HostGator).
- [ ] Quando houver reajuste do subsídio dos vereadores, atualizar `salario.faixas` em `coletor/processar.py`.
- [ ] Virada do ano (janeiro/2027): conferir se os coletores trocam de exercício sozinhos (`coletar.py` usa 2025..ano atual; Prefeitura/ITAPREV usam o ano atual; o TCE só publica com atraso; a folha pega o último mês disponível).

## Ideias pedidas ou sugeridas (ainda não feitas)

- Prefeitura: anos anteriores (2025) para comparação; restos a pagar; contratos.
- ITAPREV: carteira de investimentos e resultado atuarial (Ministério da Previdência — CADPREV/DAIR); comparação com anos anteriores.
- Câmara: despesas da própria Câmara (diárias, contratos); votos nominais se um dia forem publicados.
- Votos dos vereadores na eleição de 2024 (TSE) — oferecido, não feito.
- Alertas (ex.: mensagem quando surgir compra grande sem licitação).
