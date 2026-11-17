// Trecho comum a todos os painéis Business Charts; o montar_dashboard.py o cola antes do código de cada painel.

const PALETA = {
  claro: { clean: '#2a78d6', drink: '#eb6834', perfume: '#1baf7a', alcohol70_spray: '#eda100', alcohol70_hands: '#e87ba4', mouthwash: '#008300', outro: '#6250d6' },
  escuro: { clean: '#3987e5', drink: '#d95926', perfume: '#199e70', alcohol70_spray: '#c98500', alcohol70_hands: '#d55181', mouthwash: '#0ca30c', outro: '#9085e9' },
};
const NOMES = {
  clean: 'ambiente', drink: 'bebida', perfume: 'perfume',
  alcohol70_spray: 'álcool 70 (spray)', alcohol70_hands: 'álcool 70 (mãos)', mouthwash: 'enxaguante',
};

const detectarEscuro = () => {
  const tema = context.grafana && context.grafana.theme;
  if (tema && typeof tema.isDark === 'boolean') {
    return tema.isDark;
  }
  const rgb = (getComputedStyle(document.body).backgroundColor.match(/[\d.]+/g) || []).map(Number);
  if (rgb.length < 3 || rgb[3] === 0) {
    return false;
  }
  return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] < 128;
};
const escuro = detectarEscuro();
const tinta = escuro ? '#c3c2b7' : '#52514e';
const tintaForte = escuro ? '#f0efec' : '#0b0b0b';
const grade = escuro ? '#33332f' : '#e6e5e1';
const superficie = escuro ? '#1a1a19' : '#fcfcfb';
const cores = escuro ? PALETA.escuro : PALETA.claro;

const corDoCaso = (caso) => cores[caso] || cores.outro;
const nomeDoCaso = (caso) => NOMES[caso] || caso;
const ordenarCasos = (casos) => {
  const ordem = Object.keys(NOMES);
  const posicao = (c) => (ordem.indexOf(c) === -1 ? ordem.length : ordem.indexOf(c));
  return [...new Set(casos)].sort((a, b) => posicao(a) - posicao(b) || a.localeCompare(b));
};
const comAlfa = (hex, alfa) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alfa})`;
};

const quadro = context.panel.data.series[0];
const coluna = (nome) => {
  const campo = quadro && quadro.fields.find((f) => f.name === nome);
  return campo ? Array.from(campo.values) : [];
};
const semDados = (mensagem) => ({
  title: { text: mensagem, left: 'center', top: 'middle', textStyle: { color: tinta, fontSize: 13, fontWeight: 'normal' } },
});

const eixoValor = (extra) => Object.assign({
  type: 'value',
  scale: true,
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { color: tinta, fontSize: 11 },
  splitLine: { lineStyle: { color: grade, width: 1 } },
}, extra || {});
const eixoCategoria = (dados, extra) => Object.assign({
  type: 'category',
  data: dados,
  axisLine: { lineStyle: { color: grade } },
  axisTick: { show: false },
  axisLabel: { color: tinta, fontSize: 11 },
}, extra || {});
const tituloGrafico = (texto, extra) => Object.assign({
  text: texto,
  textStyle: { color: tintaForte, fontSize: 12, fontWeight: 600 },
}, extra || {});
const dica = (formatador) => ({
  backgroundColor: superficie,
  borderColor: grade,
  textStyle: { color: tintaForte, fontSize: 12 },
  formatter: formatador,
});
