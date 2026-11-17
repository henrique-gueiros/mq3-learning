// Boxplot por caso, um gráfico por sensor. Caixa = quartis; linhas = percentis 5 e 95; losango = média.
if (!quadro || coluna('caso').length === 0) {
  return semDados('Sem leituras para os filtros escolhidos');
}
const sensores = [['mq3', 'MQ-3', 0], ['mq135', 'MQ-135', 0], ['umid', 'Umidade (%)', 1]];
const casos = coluna('caso');
const nomes = casos.map(nomeDoCaso);
const n = coluna('n');
const arredondar = (v, casas) => (v === null || v === undefined ? '–' : v.toFixed(casas));

const title = [];
const grid = [];
const xAxis = [];
const yAxis = [];
const series = [];
sensores.forEach(([chave, rotulo, casas], i) => {
  const esquerda = 5 + i * 32;
  title.push(tituloGrafico(rotulo, { left: `${esquerda}%`, top: 6 }));
  grid.push({ left: `${esquerda}%`, top: 40, width: '27%', bottom: 34, containLabel: true });
  xAxis.push(eixoCategoria(nomes, { gridIndex: i }));
  yAxis.push(eixoValor({ gridIndex: i }));
  const p = (nome) => coluna(`${chave}_${nome}`);
  const caixas = [p('p5'), p('p25'), p('p50'), p('p75'), p('p95')];
  series.push({
    name: rotulo,
    type: 'boxplot',
    xAxisIndex: i,
    yAxisIndex: i,
    boxWidth: [10, 40],
    data: casos.map((caso, k) => ({
      value: caixas.map((c) => c[k]),
      itemStyle: { color: comAlfa(corDoCaso(caso), 0.22), borderColor: corDoCaso(caso), borderWidth: 2 },
    })),
    tooltip: {
      ...dica((x) => {
        const k = x.dataIndex;
        return `<b>${rotulo} · ${nomes[k]}</b><br/>${n[k]} leituras<br/>`
          + `mediana ${arredondar(caixas[2][k], casas)}<br/>quartis ${arredondar(caixas[1][k], casas)} a ${arredondar(caixas[3][k], casas)}<br/>`
          + `percentis 5 a 95: ${arredondar(caixas[0][k], casas)} a ${arredondar(caixas[4][k], casas)}<br/>média ${arredondar(coluna(`${chave}_media`)[k], casas)}`;
      }),
    },
  });
  series.push({
    name: `${rotulo} (média)`,
    type: 'scatter',
    xAxisIndex: i,
    yAxisIndex: i,
    symbol: 'diamond',
    symbolSize: 11,
    z: 10,
    data: casos.map((caso, k) => ({
      value: [nomes[k], coluna(`${chave}_media`)[k]],
      itemStyle: { color: corDoCaso(caso), borderColor: superficie, borderWidth: 2 },
    })),
    label: { show: true, position: 'right', color: tinta, fontSize: 10, formatter: (x) => arredondar(x.value[1], casas) },
    tooltip: { show: false },
  });
});

return { title, grid, xAxis, yAxis, series, tooltip: { trigger: 'item' } };
