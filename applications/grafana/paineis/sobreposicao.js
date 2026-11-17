// Todas as rodadas juntas: uma linha por rodada, colorida pelo caso, num gráfico por medida.
// O eixo é o tempo desde a primeira leitura de cada rodada; arraste a barra de baixo para ver rodadas mais longas.
if (!quadro || coluna('tempo_s').length === 0) {
  return semDados('Sem leituras para os filtros escolhidos');
}
const rodadaDe = coluna('rodada');
const casoDe = coluna('caso');
const tempo = coluna('tempo_s');
const medidas = [['humidity_pct', 'Umidade (%)'], ['mq135_raw', 'MQ-135'], ['ppm', 'PPM']];
const rodadas = [...new Set(rodadaDe)];
const casos = ordenarCasos(casoDe);

const linhasDaRodada = {};
rodadaDe.forEach((r, k) => {
  (linhasDaRodada[r] = linhasDaRodada[r] || []).push(k);
});

const title = [];
const grid = [];
const xAxis = [];
const yAxis = [];
const series = [];
medidas.forEach(([campo, rotulo], i) => {
  const topo = 9 + i * 27;
  title.push(tituloGrafico(rotulo, { left: 8, top: `${topo - 4}%` }));
  grid.push({ left: 8, right: 16, top: `${topo}%`, height: '17%', containLabel: true });
  xAxis.push(eixoValor({
    gridIndex: i,
    scale: false,
    min: 0,
    splitLine: { show: false },
    axisLabel: { show: i === medidas.length - 1, color: tinta, fontSize: 11 },
    name: i === medidas.length - 1 ? 'segundos desde a primeira leitura' : '',
    nameLocation: 'middle',
    nameGap: 26,
    nameTextStyle: { color: tinta },
  }));
  yAxis.push(eixoValor({ gridIndex: i }));
  const valores = coluna(campo);
  rodadas.forEach((rodada) => {
    const linhas = linhasDaRodada[rodada];
    const caso = casoDe[linhas[0]];
    series.push({
      name: nomeDoCaso(caso),
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      showSymbol: false,
      sampling: 'lttb',
      lineStyle: { color: corDoCaso(caso), width: 1.4, opacity: 0.75 },
      itemStyle: { color: corDoCaso(caso) },
      data: linhas.map((k) => [tempo[k], valores[k]]),
    });
  });
});

return {
  title,
  grid,
  xAxis,
  yAxis,
  series,
  legend: { top: 0, right: 16, data: casos.map(nomeDoCaso), textStyle: { color: tinta }, icon: 'roundRect', itemHeight: 8 },
  dataZoom: [
    { type: 'inside', xAxisIndex: [0, 1, 2], startValue: 0, endValue: 300 },
    { type: 'slider', xAxisIndex: [0, 1, 2], startValue: 0, endValue: 300, bottom: 6, height: 18, textStyle: { color: tinta } },
  ],
  axisPointer: { link: [{ xAxisIndex: 'all' }] },
  tooltip: { trigger: 'axis', ...dica((lista) => `${Math.round(lista[0].value[0])} s<br/>${lista.map((s) => `${s.seriesName}: ${s.value[1]}`).join('<br/>')}`) },
};
