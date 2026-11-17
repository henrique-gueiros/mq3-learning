# Dashboard no Grafana Cloud

O dashboard fica numa stack gratuita do Grafana Cloud. O Cloud não enxerga o
notebook, então o agente PDC (serviço `pdc` do `docker-compose.yml`) abre um
túnel de saída até a stack. Por ele o Cloud consulta o PostgreSQL e assina o
Mosquitto que rodam no Compose. Nenhuma porta do roteador é aberta.

O dashboard está versionado em `dashboards/coleta.json` (gerado por
`montar_dashboard.py`) e é publicado por `publicar.py`. Ele não usa uid fixo de data source: os seletores
**PostgreSQL** e **MQTT** no topo escolhem os data sources da stack.

Para ver o mesmo dashboard num Grafana local, sem conta, use o perfil `local` do
Compose (veja `applications/README.md`).

## Configurar a stack (uma vez)

1. Crie a conta e a stack em grafana.com (plano Free).
2. Em **Administration → Plugins and data → Plugins**, instale
   **Business Charts** (`volkovlabs-echarts-panel`) e **MQTT**
   (`grafana-mqtt-datasource`). Testado com Business Charts 7.3.0 e MQTT
   1.3.12 no Grafana 13.3. Anote aqui as versões instaladas na stack.
3. Em **Connections → Private data source connect**, crie uma rede (por
   exemplo `mq3-coleta`) e gere um token. A página mostra o comando do agente:
   copie os valores de `-token`, `-cluster` e `-gcloud-hosted-grafana-id`
   para `GCLOUD_PDC_SIGNING_TOKEN`, `GCLOUD_PDC_CLUSTER` e
   `GCLOUD_HOSTED_GRAFANA_ID` no `.env` da raiz.
4. Suba o Compose com o túnel e confira que o agente conectou:

   ```bash
   docker compose --profile cloud up -d
   docker compose logs pdc | tail
   ```

5. Em **Connections → Data sources**, crie:
   - **PostgreSQL**: host `postgres:5432`, banco `mq3`, usuário
     `grafana_leitor`, senha = `GRAFANA_PG_SENHA` do `.env`, TLS desabilitado,
     e em **Private data source connect** escolha a rede do passo 3.
   - **MQTT**: URI `tcp://mosquitto:1883`, sem usuário, e a mesma rede PDC.

   Clique em **Save & test** nos dois.
6. Em **Administration → Users and access → Service accounts**, crie uma
   conta com papel **Editor**, gere um token e coloque-o em `GRAFANA_TOKEN`.
   Em `GRAFANA_URL`, use o endereço da stack (`https://<stack>.grafana.net`).
7. Publique o dashboard, da raiz do repositório:

   ```bash
   python applications/grafana/publicar.py
   ```

## Se algo não funcionar no Cloud

- **MQTT via PDC falhou no plano Free:** troque o data source do painel
  "Leituras que chegam da placa" para o PostgreSQL com a consulta abaixo e atualização de 5 s. Os
  dados passam a vir do banco, alguns segundos atrasados.

  ```sql
  select ts as time, mq3_raw, mq135_raw, humidity_pct
  from v_leituras
  where rodada_id = (select id from rodadas where inicio is not null order by inicio desc limit 1)
  order by ts
  ```

- **Business Charts indisponível:** o heatmap pode virar uma Table nativa com
  a cor de fundo das células (cell type *Color background*). O boxplot não
  tem equivalente nativo.

## Painéis

Todos os gráficos são Business Charts (Apache ECharts); os três números do topo
são o único uso de painéis nativos, porque um número não precisa de gráfico.

| Painel | Por que esse gráfico | Fonte |
| --- | --- | --- |
| Placa, Rodadas, Leituras | Um número só: indicador, não gráfico | PostgreSQL |
| Distribuição das leituras por caso | Boxplot por sensor: mostra mediana, quartis e dispersão, que uma barra de média esconde. Losango = média | `v_leituras` |
| Média em relação ao ambiente | Heatmap divergente (azul abaixo, laranja acima, cinza igual): uma grade caso × sensor com a mesma unidade (%) | `v_leituras` |
| MQ-3 × MQ-135 por leitura | Dispersão: responde se os dois sensores juntos separam os casos | `v_leituras` |
| Todas as rodadas sobrepostas | Uma linha por rodada, colorida pelo caso, em um gráfico por medida (umidade, MQ-135, PPM): compara os casos sem escolher uma rodada. Mostra os primeiros 300 s; a barra de baixo move a janela | `v_leituras` |
| Leituras da rodada ao longo do tempo | Uma linha por sensor, cada um com sua escala (nunca dois eixos no mesmo gráfico) | `v_leituras` |
| Subida por sopro | Dispersão, um ponto por sopro marcado | `v_sopros` |
| Rodadas sem sopro marcado | Lista: são nomes de arquivos, não números | `v_rodadas_sem_sopro` |
| Leituras que chegam da placa | Linhas ao vivo, um gráfico por sensor | MQTT `mq3/placa01/leituras` |

Cada caso tem sempre a mesma cor em todos os gráficos (paleta validada, ver
`paineis/comum.js`); o caso `clean` aparece como "ambiente". Só aparecem os seletores **Caso**, **Rodada** e **Janela**;
os demais ficam ocultos (`var-incluir_simulador=sim` na URL mostra as rodadas do
simulador). A variável **Janela** escolhe entre o arquivo inteiro e só as janelas
de sopro (sopro + 30 s).

## Alterar um painel

O JavaScript de cada gráfico fica em `paineis/*.js` e as consultas em
`montar_dashboard.py`. Depois de mudar qualquer um dos dois:

```bash
python applications/grafana/montar_dashboard.py
cd applications && python -m pytest coleta/tests/test_dashboard.py
```

O teste confere que o `dashboards/coleta.json` versionado é o que o script gera e
que cada gráfico monta com dados e sem dados (precisa de `node`).

Não edite o `coleta.json` à mão nem só na interface: publicar de novo sobrescreve
qualquer edição. Mude os arquivos acima e gere o JSON.

## PPM

O ppm vem calculado pelo firmware e aparece só em `v_leituras`, para comparar
casos nos gráficos. Ele nunca entra em médias, subidas, rótulos nem features do
modelo. Um banco criado antes de 17/11/2026 precisa da migração
`applications/db/migracoes/2026-11-17-ppm-em-v_leituras.sql`.
