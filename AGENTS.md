# AGENTS.md — Sopro Seguro

Detector de álcool para carros com machine learning (ESP32 + MQ-3, MQ-135 e DHT11),
projeto acadêmico de duas disciplinas: Machine Learning e Sistemas Embarcados. Este
arquivo é a fonte única das regras; o `CLAUDE.md` só aponta para cá. A equipe está
aprendendo: prefira código claro, modular e didático, e explique conceitos com
exemplo concreto.

## Onde está o resto

- **Mapa do sistema** (peças, fluxo, contratos MQTT, banco, portas): `ARCHITECTURE.md`.
- **Estado, entregáveis, datas e próximas tarefas:** `docs/roadmap.md`.
- **Plano em andamento** (tela React): `docs/superpowers/plans/2026-11-17-frontend-react.md`.
- **Regras de cada área:** o `AGENTS.md` dentro de `applications/`, `applications/frontend/` e `ml/`.
- **Requisitos das disciplinas:** `docs/`. O `decisoes_projeto_ml.pdf` vale, exceto nas classes (ainda fala em 3); valem as duas abaixo.

## O que o modelo prevê

Cada **tentativa de sopro** recebe uma classe:

| Classe | Significado |
| --- | --- |
| `sob_efeito` | A pessoa bebeu (`drink`) |
| `sem_efeito` | Não bebeu: ar limpo, perfume, álcool em gel, borrifo, enxaguante |

Perfume, álcool 70% e enxaguante estão na coleta para o modelo separar vapor no
ambiente de motorista que bebeu. O sistema não mede mg/L: `sob_efeito` é "bebeu nas
condições do experimento", não laudo. O que fazer depois de uma detecção (alerta,
bloqueio) ainda não foi decidido.

## Regras invioláveis

- **Dados só da coleta da equipe**: nada de datasets da internet nem dados sintéticos em treino ou teste. Os CSVs de sessão ficam **sem edição**; derivados vão para `ml/data/processed/`.
- `ppm` e `alcool` são calculados pelo firmware a partir do MQ-3: ficam **fora** de rótulos, features e regras de decisão (podem ser exibidos). O rótulo vem da `condition` anotada.
- Medições, calibração, limiares, resultados e fontes vêm de dados ou documentos reais; o que ainda não foi medido é tratado como hipótese, e está escrito assim.
- Métricas de testes automatizados (curvas montadas à mão) não são desempenho real.
- Relatório da disciplina: a equipe escreve. Agentes só revisam texto da equipe e produzem código, figuras e tabelas de resultados.
- Testes com álcool: supervisionados, ventilados, longe de chama, sem ninguém dirigindo. Coletar com pessoas que beberam exige Comitê de Ética e termo de consentimento.
- `esp32-esp8266/` é mantido por outro integrante: mude só quando a tarefa pedir. Renomear ou reorganizar pastas é decisão da equipe.
- Horário ou dia da semana como preditor só com justificativa e avaliação.

## Fluxo de trabalho

1. Inspecione o repositório antes de criar algo; preserve o que existe. Trabalhe em etapas pequenas, uma por vez.
2. TDD onde o comportamento é verificável: teste primeiro, vendo falhar, depois o código.
3. Antes de cada commit, rode a revisão de código (skill `code-review`) sobre o diff e corrija o que for válido.
4. Ao fechar uma etapa de um plano, atualize o plano (andamento e o detalhe do que falta) no mesmo commit.
5. Mensagens de commit em português, descrevendo o porquê, sem linha de coautoria de agente.
6. Ao terminar, diga o que mudou, como executar e o que foi testado.

Código: Python 3.9+ com tipos e docstring nas funções públicas; um só ambiente
(`ml/.venv`); caminhos relativos ao repositório. Textos de tela e documentação em português.
