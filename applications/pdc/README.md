# Agente PDC

O agente do Private Data Source Connect é o serviço `pdc` do
`docker-compose.yml` (imagem `grafana/pdc-agent:0.0.67`). Ele só sobe com o
perfil `cloud`, para que o Compose funcione sem uma stack configurada:

```bash
docker compose --profile cloud up -d
```

Ele abre uma conexão de saída até o Grafana Cloud e deixa a stack alcançar,
pela rede interna do Compose, `postgres:5432` e `mosquitto:1883`. Os valores
do `.env` e a configuração dos data sources estão em
[`../grafana/README.md`](../grafana/README.md).

Rode o perfil `cloud` numa máquina só (a da coleta ou a da apresentação).
Com dois agentes usando o mesmo token, o Cloud alternaria entre dois bancos
diferentes.
