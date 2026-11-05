const chartElement = document.querySelector('#visit-chart');
const dataElement = document.querySelector('#chart-data');

if (chartElement && dataElement) {
  const series = JSON.parse(dataElement.textContent);
  const buttons = [...document.querySelectorAll('[data-range]')];
  const namespace = 'http://www.w3.org/2000/svg';
  const fa = value => Number(value).toLocaleString('fa-IR');

  function appendSvg(parent, name, attributes = {}, text = '') {
    const element = document.createElementNS(namespace, name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text) element.textContent = text;
    parent.append(element);
    return element;
  }

  function renderChart(range) {
    const values = series[range] || [];
    const width = 800;
    const height = 270;
    const left = 54;
    const right = 12;
    const top = 14;
    const bottom = 32;
    const max = Math.max(1, ...values.map(item => item.value));
    const x = index => left + (width - left - right) * index / Math.max(1, values.length - 1);
    const y = value => top + (height - top - bottom) * (1 - value / max);
    const svg = appendSvg(document.createDocumentFragment(), 'svg', {
      class: 'chart', viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': 'نمودار تعداد بازدیدها',
    });
    const defs = appendSvg(svg, 'defs');
    const gradient = appendSvg(defs, 'linearGradient', {id: 'visit-fill', x1: '0', y1: '0', x2: '0', y2: '1'});
    appendSvg(gradient, 'stop', {offset: '0', 'stop-color': '#d4d6e2', 'stop-opacity': '.35'});
    appendSvg(gradient, 'stop', {offset: '1', 'stop-color': '#d4d6e2', 'stop-opacity': '0'});

    for (let index = 0; index <= 4; index += 1) {
      const value = max * index / 4;
      const lineY = y(value);
      appendSvg(svg, 'line', {
        x1: left, x2: width - right, y1: lineY, y2: lineY, stroke: 'rgba(232,232,236,.1)',
      });
      appendSvg(svg, 'text', {x: left - 8, y: lineY + 4, 'text-anchor': 'end'}, fa(Math.round(value)));
    }

    if (values.length) {
      const points = values.map((item, index) => [x(index), y(item.value)]);
      const line = points.map((point, index) => `${index ? 'L' : 'M'}${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join('');
      const area = `${line}L${points.at(-1)[0].toFixed(1)} ${height - bottom}L${left} ${height - bottom}Z`;
      appendSvg(svg, 'path', {d: area, fill: 'url(#visit-fill)'});
      appendSvg(svg, 'path', {d: line, fill: 'none', stroke: '#e8e8ec', 'stroke-width': '2'});

      const labelStep = Math.ceil(values.length / 10);
      points.forEach((point, index) => {
        const circle = appendSvg(svg, 'circle', {
          cx: point[0], cy: point[1], r: 4, fill: '#0e1018', stroke: '#e8e8ec', 'stroke-width': '1.6',
        });
        appendSvg(circle, 'title', {}, `${values[index].label}: ${fa(values[index].value)} بازدید`);
        if (index % labelStep === 0 || index === values.length - 1) {
          appendSvg(svg, 'text', {x: point[0], y: height - 8, 'text-anchor': 'middle'}, values[index].label);
        }
      });
    }

    chartElement.replaceChildren(svg);
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.range === range)));
  }

  buttons.forEach(button => button.addEventListener('click', () => renderChart(button.dataset.range)));
  renderChart('d');
}
