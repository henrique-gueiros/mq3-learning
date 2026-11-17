// Uma rodada: um gráfico por sensor, mesmo eixo de tempo. A faixa cinza é a janela de sopro (sopro + 30 s).
if (!quadro || coluna('tempo_s').length === 0) {
  return semDados('Escolha uma rodada com leituras');
}
const tempo = coluna('tempo_s');
const emSopro = coluna('em_sopro');
const cor = corDoCaso(coluna('caso')[0]);
const sensores = [['mq3_raw', 'MQ-3'], ['mq135_raw', 'MQ-135'], ['humidity_pct', 'Umidade (%)']];

const faixas = [];
let inicio = null;
emSopro.forEach((dentro, k) => {
  if (dentro && inicio === null) {
    inicio = tempo[k];
  }
  if (!dentro && inicio !== null) {
    faixas.push([{ xAxis: inicio }, { xAxis: tempo[k - 1] }]);
    inicio = null;
  }
});
if (inicio !== null) {
  faixas.push([{ xAxis: inicio }, { xAxis: tempo[tempo.length - 1] }]);
}

const title = [];
const grid = [];
const xAxis = [];
const yAxis = [];
const series = [];
sensores.forEach(([campo, rotulo], i) => {
  const topo = 4 + i * 29;
  title.push(tituloGrafico(rotulo, { left: 8, top: `${topo}%` }));
  grid.push({ left: 8, right: 16, top: `${topo + 5}%`, height: '17%', containLabel: true });
  xAxis.push(eixoValor({
    gridIndex: i,
    scale: false,
    min: 0,
    splitLine: { show: false },
    axisLabel: { show: i === sensores.length - 1, color: tinta, fontSize: 11 },
    name: i === sensores.length - 1 ? 'segundos desde a primeira leitura' : '',
    nameLocation: 'middle',
    nameGap: 26,
    nameTextStyle: { color: tinta },
  }));
  yAxis.push(eixoValor({ gridIndex: i }));
  const valores = coluna(campo);
  series.push({
    name: rotulo,
    type: 'line',
    xAxisIndex: i,
    yAxisIndex: i,
    showSymbol: false,
    lineStyle: { color: cor, width: 2 },
    itemStyle: { color: cor },
    data: tempo.map((t, k) => [t, valores[k]]),
    markArea: { silent: true, itemStyle: { color: comAlfa(tinta, 0.14) }, data: faixas },
  });
});

return {
  title,
  grid,
  xAxis,
  yAxis,
  series,
  axisPointer: { link: [{ xAxisIndex: 'all' }] },
  tooltip: { trigger: 'axis', ...dica((lista) => `${Math.round(lista[0].value[0])} s<br/>${lista.map((s) => `${s.seriesName}: ${s.value[1]}`).join('<br/>')}`) },
};
