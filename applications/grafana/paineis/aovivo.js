// Leituras que chegam pelo MQTT, um gráfico por sensor, no mesmo eixo de tempo.
const tempoCampo = quadro && quadro.fields.find((f) => f.type === 'time');
if (!quadro || !tempoCampo || tempoCampo.values.length === 0) {
  return semDados('Aguardando leituras da placa');
}
const tempo = Array.from(tempoCampo.values);
const sensores = [['mq3_raw', 'MQ-3'], ['mq135_raw', 'MQ-135'], ['humidity_pct', 'Umidade (%)']];
const cor = cores.outro;

const title = [];
const grid = [];
const xAxis = [];
const yAxis = [];
const series = [];
sensores.forEach(([campo, rotulo], i) => {
  const topo = 4 + i * 29;
  title.push(tituloGrafico(rotulo, { left: 8, top: `${topo}%` }));
  grid.push({ left: 8, right: 16, top: `${topo + 5}%`, height: '17%', containLabel: true });
  xAxis.push({
    type: 'time',
    gridIndex: i,
    axisLine: { lineStyle: { color: grade } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { show: i === sensores.length - 1, color: tinta, fontSize: 11 },
  });
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
  });
});

return {
  title,
  grid,
  xAxis,
  yAxis,
  series,
  animation: false,
  axisPointer: { link: [{ xAxisIndex: 'all' }] },
  tooltip: { trigger: 'axis', ...dica((lista) => lista.map((s) => `${s.seriesName}: ${s.value[1]}`).join('<br/>')) },
};
