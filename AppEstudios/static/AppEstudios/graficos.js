/* Local SVG charts. Every mark is a real, keyboard-accessible link. */
(() => {
  'use strict';
  // Keep the current destination visible inside the mobile navigation strip.
  const navigation = document.querySelector('nav.global');
  const selected = navigation?.querySelector('[aria-current="page"]');
  if (selected && matchMedia('(max-width: 650px)').matches) {
    navigation.scrollLeft += selected.getBoundingClientRect().left - navigation.getBoundingClientRect().left - 10;
  }
  const NS = 'http://www.w3.org/2000/svg';
  const format = n => new Intl.NumberFormat('es-CL', {maximumFractionDigits: 2}).format(n);
  const element = (tag, attributes = {}, text) => {
    const node = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function reveal(hash) {
    const target = document.getElementById(hash.replace(/^#/, ''));
    if (!target) return;
    let parent = target;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
  }
  addEventListener('hashchange', () => reveal(location.hash));
  reveal(location.hash);

  document.querySelectorAll('.interactive-chart').forEach(section => {
    const data = JSON.parse(section.querySelector('script[type="application/json"]').textContent);
    if (!data.points.length) return;
    const canvas = section.querySelector('[data-canvas]');
    const readout = section.querySelector('[data-readout]');
    const sort = section.querySelector('[data-sort]');
    function draw() {
      const points = data.points.slice();
      if (sort && sort.value !== 'original') points.sort((a, b) => sort.value === 'asc' ? a.value - b.value : b.value - a.value);
      const width = Math.max(290, canvas.clientWidth);
      const horizontal = data.type === 'barras' || (data.type === 'puntos' && data.orientacion !== 'vertical');
      const height = horizontal ? Math.max(180, points.length * 34 + 55) : data.type === 'calor' ? 250 : 290;
      const svg = element('svg', {viewBox: `0 0 ${width} ${height}`, role: 'group', 'aria-label': `${data.title}. ${data.period}. ${data.unit}.`, class: 'chart-svg'});
      svg.append(element('title', {}, data.title));
      const minimum = data.unit === 'nota' && data.type !== 'barras' ? 1 : 0;
      const maximum = data.max;
      const ticks = data.unit === 'nota' ? (width < 450 ? [minimum, 4, 7] : [minimum, 2, 3, 4, 5, 6, 7]) : Array.from({length: 5}, (_, i) => maximum * i / 4);
      const label = (x, y, text, extra = {}) => element('text', {x, y, class: 'axis-label', ...extra}, text);
      function mark(point) {
        const description = `${point.label}: ${format(point.value)} ${data.unit}. Ver detalle.`;
        const link = element('a', {href: point.url, tabindex: 0, class: 'chart-mark', 'aria-label': description});
        link.append(element('title', {}, description));
        for (const event of ['pointerenter', 'focus']) link.addEventListener(event, () => {readout.textContent = description;});
        link.addEventListener('click', () => {if (point.url.startsWith('#')) reveal(point.url);});
        link.addEventListener('keydown', event => {
          if (event.key === ' ') {event.preventDefault(); reveal(point.url); location.href = point.url;}
        });
        return link;
      }
      function horizontalChart() {
        const left = Math.min(175, width * .40), right = width - 40, bottom = height - 30;
        const x = value => left + (right - left) * (value - minimum) / (maximum - minimum);
        ticks.forEach(tick => {
          svg.append(element('line', {x1: x(tick), y1: 8, x2: x(tick), y2: bottom - 12, class: 'grid-line'}));
          svg.append(label(x(tick), bottom + 10, format(tick), {'text-anchor': 'middle'}));
        });
        if (data.referencia) svg.append(element('line', {x1: x(data.referencia), y1: 8, x2: x(data.referencia), y2: bottom - 12, class: 'reference-line'}));
        points.forEach((point, i) => {
          const y = 18 + i * 34;
          const a = mark(point);
          const maxLabel = width < 450 ? 16 : 25;
          a.append(element('rect', {x: 0, y: y - 10, width, height: 32, fill: 'transparent'}));
          a.append(label(left - 12, y + 10, point.label.length > maxLabel ? point.label.slice(0, maxLabel - 1) + '…' : point.label, {'text-anchor': 'end', class: 'point-label'}));
          if (data.type === 'puntos') {
            a.append(element('line', {x1: left, y1: y + 5, x2: x(point.value), y2: y + 5, stroke: point.color, 'stroke-opacity': .18, 'stroke-width': 4}));
            a.append(element('circle', {cx: x(point.value), cy: y + 5, r: 6, fill: point.color, class: 'data-shape'}));
          } else {
            a.append(element('rect', {x: left, y: y - 5, width: Math.max(1, x(point.value) - left), height: 20, rx: 4, fill: point.color, class: 'data-shape'}));
          }
          a.append(label(right + 10, y + 10, format(point.value), {class: 'point-value'}));
          svg.append(a);
        });
      }
      function verticalChart() {
        const left = 36, right = width - 20, top = 22, bottom = height - 48;
        const y = value => bottom - (bottom - top) * (value - minimum) / (maximum - minimum);
        const columns = ['histograma', 'columnas'].includes(data.type);
        const slot = (right - left) / points.length;
        const x = i => columns ? left + slot * (i + .5) : left + 15 + (right - left - 30) * i / Math.max(points.length - 1, 1);
        ticks.forEach(tick => {
          svg.append(element('line', {x1: left, y1: y(tick), x2: right, y2: y(tick), class: 'grid-line'}));
          svg.append(label(left - 8, y(tick) + 4, format(tick), {'text-anchor': 'end'}));
        });
        if (data.referencia) {
          svg.append(element('line', {x1: left, y1: y(data.referencia), x2: right, y2: y(data.referencia), class: 'reference-line'}));
          svg.append(label(right, y(data.referencia) - 7, 'Referencia 4,0', {'text-anchor': 'end'}));
        }
        if (data.type === 'linea') svg.append(element('polyline', {points: points.map((p, i) => `${x(i)},${y(p.value)}`).join(' '), class: 'trend-line'}));
        const labelEvery = Math.max(1, Math.ceil(points.length / (width < 450 ? 5 : 8)));
        points.forEach((point, i) => {
          const a = mark(point);
          if (columns) {
            const barWidth = slot * (data.type === 'histograma' ? .94 : .56);
            a.append(element('rect', {x: x(i) - barWidth / 2, y: top, width: barWidth, height: bottom - top, fill: 'transparent'}));
            a.append(element('rect', {x: x(i) - barWidth / 2, y: y(point.value), width: barWidth, height: Math.max(1, bottom - y(point.value)), rx: data.type === 'histograma' ? 2 : 4, fill: point.color, class: 'data-shape'}));
            svg.append(label(x(i), y(point.value) - 8, format(point.value), {'text-anchor': 'middle'}));
          } else {
            a.append(element('circle', {cx: x(i), cy: y(point.value), r: 14, fill: 'transparent'}));
            a.append(element('circle', {cx: x(i), cy: y(point.value), r: 5.5, fill: point.color, stroke: 'white', 'stroke-width': 2, class: 'data-shape'}));
            if (points.length <= 10) svg.append(label(x(i), y(point.value) - 13, format(point.value), {'text-anchor': 'middle'}));
          }
          if (i % labelEvery === 0 || i === points.length - 1) {
            const text = data.id === 'notas' ? String(i + 1 + Number(data.offset || 0)) : point.label;
            svg.append(label(x(i), bottom + 24, text, {'text-anchor': 'middle'}));
          }
          svg.append(a);
        });
        svg.append(label(right, height - 3, data.id === 'notas' ? 'Orden de registro' : data.type === 'histograma' ? 'Promedio del estudiante' : '', {'text-anchor': 'end'}));
      }
      function donutChart() {
        const total = points.reduce((sum, p) => sum + p.value, 0);
        const cx = width / 2, cy = 130, outer = 98, inner = 69;
        const coords = (r, angle) => [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
        let start = -Math.PI / 2;
        points.forEach(point => {
          if (point.value <= 0) return;
          const end = start + Math.min(point.value / total * 2 * Math.PI, 2 * Math.PI - .0001);
          const large = end - start > Math.PI ? 1 : 0;
          const a = mark(point);
          const path = `M ${coords(outer, start)} A ${outer},${outer} 0 ${large},1 ${coords(outer, end)} L ${coords(inner, end)} A ${inner},${inner} 0 ${large},0 ${coords(inner, start)} Z`;
          a.append(element('path', {d: path, fill: point.color, stroke: 'white', 'stroke-width': 3, class: 'data-shape'}));
          svg.append(a);
          start = end;
        });
        svg.append(label(cx, cy + 2, format(total), {'text-anchor': 'middle', class: 'donut-total'}));
        svg.append(label(cx, cy + 25, 'min registrados', {'text-anchor': 'middle'}));
      }
      function heatmapChart() {
        const left = 65, top = 32, gap = 6, cellWidth = (width - left - 12) / 7, cellHeight = 38;
        data.columns.forEach((text, i) => svg.append(label(left + cellWidth * (i + .5), 17, text, {'text-anchor': 'middle'})));
        data.rows.forEach((text, i) => svg.append(label(left - 8, top + cellHeight * (i + .5), text.replace('Semana ', 'Sem. '), {'text-anchor': 'end'})));
        points.forEach(point => {
          const a = mark(point), x = left + point.column * cellWidth, y = top + point.row * cellHeight;
          a.append(element('rect', {x, y, width: cellWidth - gap, height: cellHeight - gap, rx: 5, fill: point.value ? point.color : '#edf0f7', 'fill-opacity': point.value ? .22 + .78 * point.value / maximum : 1, class: 'data-shape'}));
          a.append(label(x + (cellWidth - gap) / 2, y + 21, point.label.slice(0, 2), {'text-anchor': 'middle', style: point.value / maximum > .8 ? 'fill:white' : 'fill:#3f4361'}));
          svg.append(a);
        });
        svg.append(label(left, 218, 'Menos', {}));
        for (let i = 0; i < 5; i++) svg.append(element('rect', {x: left + 48 + i * 20, y: 204, width: 15, height: 15, rx: 3, fill: '#635bff', 'fill-opacity': .12 + i * .22}));
        svg.append(label(left + 155, 218, 'Más minutos registrados', {}));
      }
      if (horizontal) horizontalChart();
      else if (data.type === 'anillo') donutChart();
      else if (data.type === 'calor') heatmapChart();
      else verticalChart();
      canvas.replaceChildren(svg);
      const legend = section.querySelector('[data-legend]');
      if (legend) {
        legend.replaceChildren();
        if (data.type === 'anillo') points.forEach(point => {
          const a = document.createElement('a');
          a.href = point.url;
          const swatch = document.createElement('span');
          swatch.className = 'legend-swatch';
          swatch.style.backgroundColor = point.color;
          a.append(swatch, `${point.label} · ${format(point.value)} min`);
          legend.append(a);
        });
      }
    }
    if (sort) sort.addEventListener('change', draw);
    let lastWidth = canvas.clientWidth;
    new ResizeObserver(() => {if (canvas.clientWidth !== lastWidth) {lastWidth = canvas.clientWidth; draw();}}).observe(canvas);
    draw();
  });
})();
