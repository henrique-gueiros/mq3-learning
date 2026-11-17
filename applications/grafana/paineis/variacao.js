// Média de cada caso em relação ao ar limpo, por sensor. Azul = abaixo, laranja = acima, cinza = igual.
if (!quadro || coluna('caso').length === 0) {
  return semDados('Sem ar limpo para comparar');
}
const casos = ordenarCasos(coluna('caso'));
const casoDe = coluna('caso');
const sensores = [['mq3', 'MQ-3'], ['mq135', 'MQ-135'], ['umid', 'Umidade (%)']];
const celulas = [];
casos.forEach((caso, linha) => {
  sensores.forEach(([chave], c) => {
    const valor = coluna(chave)[casoDe.indexOf(caso)];
    if (valor !== null && valor !== undefined) {
      celulas.push([c, linha, Math.round(valor)]);
    }
  });
});
const limite = Math.max(10, ...celulas.map((c) => Math.abs(c[2])));

return {
  grid: { left: 8, right: 16, top: 12, bottom: 56, containLabel: true },
  xAxis: eixoCategoria(sensores.map((s) => s[1]), { splitArea: { show: false } }),
  yAxis: eixoCategoria(casos.map(nomeDoCaso), { axisLine: { show: false } }),
  visualMap: {
    min: -limite,
    max: limite,
    orient: 'horizontal',
    left: 'center',
    bottom: 0,
    calculable: false,
    text: ['mais alto que o ar limpo', 'mais baixo'],
    textStyle: { color: tinta },
    inRange: { color: [cores.clean, escuro ? '#3a3a38' : '#e6e5e1', cores.drink] },
  },
  tooltip: dica((x) => `<b>${nomeDoCaso(casos[x.value[1]])} · ${sensores[x.value[0]][1]}</b><br/>${x.value[2] > 0 ? '+' : ''}${x.value[2]}% em relação ao ar limpo`),
  series: [{
    type: 'heatmap',
    data: celulas,
    itemStyle: { borderColor: superficie, borderWidth: 2 },
    label: {
      show: true,
      formatter: (x) => `${x.value[2] > 0 ? '+' : ''}${x.value[2]}%`,
      color: tintaForte,
      fontSize: 12,
    },
  }],
};
