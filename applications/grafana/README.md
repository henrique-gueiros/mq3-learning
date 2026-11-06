# Dashboard no Grafana Cloud

O dashboard fica numa stack gratuita do Grafana Cloud. O Cloud não enxerga o
notebook, então o agente PDC (serviço `pdc` do `docker-compose.yml`) abre um
túnel de saída até a stack. Por ele o Cloud consulta o PostgreSQL e assina o
Mosquitto que rodam no Compose. Nenhuma porta do roteador é aberta.

O dashboard está versionado em `dashboards/coleta.json` e é publicado por
`publicar.py`. Ele não usa uid fixo de data source: os seletores
**PostgreSQL** e **MQTT** no topo escolhem os data sources da stack.

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
  "Ao vivo" para o PostgreSQL com a consulta abaixo e atualização de 5 s. Os
  dados passam a vir do banco, alguns segundos atrasados.

  ```sql
  select ts as time, mq3_raw as "MQ-3", mq135_raw as "MQ-135",
         humidity_pct as "Umidade (%)", temperature_c as "Temperatura (°C)"
  from v_leituras
  where rodada_id = (select id from rodadas where inicio is not null order by inicio desc limit 1)
  order by ts
  ```

- **Business Charts indisponível:** o heatmap pode virar uma Table nativa com
  a cor de fundo das células (cell type *Color background*). O boxplot não
  tem equivalente nativo.

## Painéis

| Painel | Fonte |
| --- | --- |
| Ao vivo: leituras da placa | MQTT `mq3/placa01/leituras` |
| Placa (recebendo/parada) e rodada atual | PostgreSQL |
| Média por caso (tabela e barras) | `v_media_rodada`: média das médias de cada rodada |
| Boxplot por caso | `v_leituras` (Business Charts) |
| Heatmap caso × sensor | `v_media_rodada` (Business Charts), cor normalizada por sensor |
| Subida por sopro: MQ-135 × MQ-3 | `v_sopros` (XY chart nativo), um ponto por sopro |
| Rodadas sem sopro marcado | `v_rodadas_sem_sopro` |
| Histórico da rodada selecionada | `v_leituras`, com os sopros como anotações |
| Resultado do modelo | reservado |

A variável **Janela** escolhe entre o arquivo inteiro e só as janelas de
sopro (sopro + 30 s). **Incluir simulador** fica em `nao` por padrão, para
que demonstrações não se misturem com a coleta.

Editou o dashboard na interface? Exporte o JSON (**Share → Export → Save to
file**, sem marcar *Export for sharing externally*) para
`dashboards/coleta.json` antes de publicar de novo, senão a edição é
sobrescrita.
