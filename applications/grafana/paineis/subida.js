// Um ponto por sopro marcado: quanto cada sensor subiu em relação à linha de base de antes do sopro.
if (!quadro || coluna('caso').length === 0) {
  return semDados('Nenhum sopro marcado ainda');
}
const casoDe = coluna('caso');
const mq3 = coluna('subida_mq3');
const mq135 = coluna('subida_mq135');

return {
  legend: { top: 4, textStyle: { color: tinta }, icon: 'circle', itemHeight: 9 },
  grid: { left: 8, right: 16, top: 44, bottom: 8, containLabel: true },
  xAxis: eixoValor({ name: 'subida do MQ-3', nameLocation: 'middle', nameGap: 28, nameTextStyle: { color: tinta } }),
  yAxis: eixoValor({ name: 'subida do MQ-135', nameLocation: 'middle', nameGap: 44, nameTextStyle: { color: tinta } }),
  tooltip: dica((x) => `<b>${x.seriesName}</b><br/>MQ-3 +${x.value[0]}<br/>MQ-135 +${x.value[1]}`),
  series: ordenarCasos(casoDe).map((caso) => ({
    name: nomeDoCaso(caso),
    type: 'scatter',
    symbolSize: 12,
    itemStyle: { color: corDoCaso(caso), borderColor: superficie, borderWidth: 2 },
    data: casoDe.map((c, k) => (c === caso ? [mq3[k], mq135[k]] : null)).filter((d) => d !== null),
  })),
};
