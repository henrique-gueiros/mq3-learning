// Cada ponto é uma leitura; a cor é o caso. Mostra se o MQ-3 e o MQ-135 juntos separam os casos.
if (!quadro || coluna('caso').length === 0) {
  return semDados('Sem leituras para os filtros escolhidos');
}
const casoDe = coluna('caso');
const mq3 = coluna('mq3_raw');
const mq135 = coluna('mq135_raw');
const casos = ordenarCasos(casoDe);

return {
  legend: { top: 4, textStyle: { color: tinta }, icon: 'circle', itemHeight: 9 },
  grid: { left: 8, right: 16, top: 44, bottom: 8, containLabel: true },
  xAxis: eixoValor({ name: 'MQ-3 (leitura bruta)', nameLocation: 'middle', nameGap: 28, nameTextStyle: { color: tinta } }),
  yAxis: eixoValor({ name: 'MQ-135 (leitura bruta)', nameLocation: 'middle', nameGap: 44, nameTextStyle: { color: tinta } }),
  tooltip: dica((x) => `<b>${x.seriesName}</b><br/>MQ-3 ${x.value[0]}<br/>MQ-135 ${x.value[1]}`),
  series: casos.map((caso) => ({
    name: nomeDoCaso(caso),
    type: 'scatter',
    symbolSize: 7,
    itemStyle: { color: comAlfa(corDoCaso(caso), 0.6), borderColor: superficie, borderWidth: 1 },
    data: casoDe.map((c, k) => (c === caso ? [mq3[k], mq135[k]] : null)).filter((d) => d !== null),
  })),
};
