/* Visualizações dinâmicas inspiradas em worldcup-r/visualizations (Fjelstul DB) */
(function (global) {
  const COLORS = { W: '#1e4d8c', D: '#6a9fd8', L: '#c44d4d', E: '#2a3a30' };
  const KO_GROUP = '#3a8fd8';
  const KO_KNOCK = '#d64040';

  function genderKey(f) {
    return f.gender || 'all';
  }

  function pickBucket(obj, f) {
    return obj[genderKey(f)] || obj.all;
  }

  function filterH2H(events, teamA, teamB) {
    const pair = new Set([teamA, teamB]);
    const matchPair = (a, b) => pair.has(a) && pair.has(b) && a !== b;
    return {
      goals: events.goals.filter((g) => matchPair(g[0], g[1])),
      matches: events.matches.filter((m) => matchPair(m[0], m[1])),
      bookings: events.bookings.filter((b) => matchPair(b[0], b[1])),
    };
  }

  function poisson(k, lambda) {
    if (lambda <= 0) return k === 0 ? 1 : 0;
    let p = Math.exp(-lambda);
    for (let i = 1; i <= k; i++) p *= lambda / i;
    return p;
  }

  function drawMatchResultsHeatmap(canvas, data, highlightTeam) {
    if (!data || !data.years.length) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const teams = [];
    data.confederations.forEach((c) => {
      c.teams.forEach((t) => teams.push({ ...t, conf: c.code }));
    });
    const cell = 11;
    const gap = 2;
    const confH = 18;
    const yearW = 42;
    const labelH = 90;
    const colW = cell + gap;

    const yearOffsets = [];
    let yAcc = labelH + confH;
    const yearHeights = data.years.map((year) => {
      const maxM = data.max_matches[String(year)] || 1;
      const h = maxM * cell + Math.max(0, maxM - 1) * gap + 6;
      yearOffsets.push(yAcc);
      yAcc += h;
      return h;
    });

    const w = yearW + teams.length * colW + 24;
    const h = yAcc + 36;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#122018';
    ctx.fillRect(0, 0, w, h);

    let x0 = yearW;
    let lastConf = '';
    teams.forEach((t) => {
      if (t.conf !== lastConf) {
        ctx.fillStyle = '#8ab098';
        ctx.font = 'bold 10px sans-serif';
        ctx.fillText(t.conf, x0 + 2, 14);
        lastConf = t.conf;
      }
      const isHi = highlightTeam && t.team === highlightTeam;
      if (isHi) {
        ctx.fillStyle = 'rgba(240,180,41,0.12)';
        ctx.fillRect(x0 - 1, labelH, colW + 1, h - labelH - 28);
      }
      ctx.save();
      ctx.translate(x0 + cell / 2, labelH - 6);
      ctx.rotate(-Math.PI / 2);
      ctx.fillStyle = isHi ? '#f0b429' : '#8ab098';
      ctx.font = (isHi ? 'bold ' : '') + '9px sans-serif';
      ctx.textAlign = 'left';
      const label = t.team.length > 14 ? t.team.slice(0, 13) + '…' : t.team;
      ctx.fillText(label, 0, 0);
      ctx.restore();

      data.years.forEach((year, yi) => {
        const seq = t.years[String(year)] || '';
        const y = yearOffsets[yi];
        for (let j = 0; j < seq.length; j++) {
          ctx.fillStyle = COLORS[seq[j]] || '#333';
          ctx.fillRect(x0, y + j * (cell + gap), cell, cell);
        }
      });
      x0 += colW;
    });

    ctx.fillStyle = '#6a8f72';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    data.years.forEach((year, yi) => {
      const y = yearOffsets[yi] + yearHeights[yi] / 2 + 3;
      ctx.fillText(year, yearW - 8, y);
    });

    const legY = h - 16;
    [['W', 'Vitória'], ['D', 'Empate'], ['L', 'Derrota'], ['E', 'Eliminado']].forEach(([k, lbl], i) => {
      const lx = 10 + i * 80;
      ctx.fillStyle = COLORS[k];
      ctx.fillRect(lx, legY, 10, 10);
      ctx.fillStyle = '#6a8f72';
      ctx.textAlign = 'left';
      ctx.font = '9px sans-serif';
      ctx.fillText(lbl, lx + 14, legY + 8);
    });
  }

  function renderPenaltiesChart(chartRef, data, topN = 14) {
    const rows = data.slice(0, topN);
    const labels = rows.map((r) => r.team);
    const scored = rows.map((r) => r.scored);
    const missed = rows.map((r) => r.missed);
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(chartRef.canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Convertidos', data: scored, backgroundColor: '#3a8fd8', borderRadius: 2 },
          { label: 'Perdidos', data: missed, backgroundColor: '#e8808a', borderRadius: 2 },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#8ab098', boxWidth: 10 } } },
        scales: {
          x: { stacked: true, ticks: { color: '#6a8f72' }, grid: { color: '#1a2e20' } },
          y: { stacked: true, ticks: { color: '#e8f0e8', font: { size: 9 } }, grid: { display: false } },
        },
      },
    });
  }

  function renderConfGoalsChart(chartRef, pairs, title, color) {
    const labels = pairs.map((p) => p[0]);
    const values = pairs.map((p) => p[1]);
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new Chart(chartRef.canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'Gols', data: values, backgroundColor: color, borderRadius: 3 }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, title: { display: false } },
        scales: {
          x: { ticks: { color: '#6a8f72' }, grid: { color: '#1a2e20' } },
          y: { ticks: { color: '#e8f0e8', font: { size: 9 } }, grid: { display: false } },
        },
      },
    });
  }

  function jitter(seed) {
    return ((seed * 9301 + 49297) % 233280) / 233280 - 0.5;
  }

  function drawMinuteScatter(canvas, points, teams, kind) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 360;
    const h = 280;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#122018';
    ctx.fillRect(0, 0, w, h);

    const margin = { t: 20, b: 28, l: 40, r: 90 };
    const plotW = (w - margin.l - margin.r) / 2;
    const plotH = h - margin.t - margin.b;

    [45, 90].forEach((min) => {
      const y = margin.t + ((min - 1) / 119) * plotH;
      ctx.strokeStyle = '#1f3828';
      ctx.beginPath();
      ctx.moveTo(margin.l, y);
      ctx.lineTo(w - margin.r, y);
      ctx.stroke();
    });
    ctx.fillStyle = 'rgba(26,46,32,0.5)';
    ctx.fillRect(margin.l, margin.t + (89 / 119) * plotH, w - margin.l - margin.r, plotH * (31 / 119));

    ctx.fillStyle = '#6a8f72';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    teams.forEach((team, ti) => {
      const cx = margin.l + plotW * ti + plotW / 2;
      ctx.fillText(team, cx, h - 8);
    });
    ['1º tempo', '2º tempo', 'Prorrogação'].forEach((lbl, i) => {
      ctx.fillText(lbl, w - margin.r + 36, margin.t + plotH * (i * 0.33 + 0.12));
    });

    points.forEach((p, idx) => {
      const teamIdx = teams.indexOf(p.team);
      if (teamIdx < 0) return;
      const cx = margin.l + plotW * teamIdx + plotW / 2 + jitter(idx) * (plotW * 0.35);
      const cy = margin.t + ((p.minute - 1) / 119) * plotH;
      const stroke = p.ko ? KO_KNOCK : KO_GROUP;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.5;
      if (kind === 'goals') {
        if (p.og) {
          ctx.strokeRect(cx - 4, cy - 4, 8, 8);
        } else if (p.pen) {
          ctx.beginPath();
          ctx.moveTo(cx, cy - 5);
          ctx.lineTo(cx + 5, cy + 4);
          ctx.lineTo(cx - 5, cy + 4);
          ctx.closePath();
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.arc(cx, cy, 4, 0, Math.PI * 2);
          ctx.stroke();
        }
      } else {
        if (p.type === 'red') {
          ctx.fillStyle = stroke;
          ctx.fillRect(cx - 4, cy - 5, 8, 10);
        } else if (p.type === 'second') {
          ctx.strokeRect(cx - 4, cy - 4, 8, 8);
        } else {
          ctx.beginPath();
          ctx.arc(cx, cy, 4, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
    });
  }

  function drawLollipop(canvas, matches, teams) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 400;
    const h = 260;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#122018';
    ctx.fillRect(0, 0, w, h);

    const margin = { t: 16, b: 24, l: 10, r: 10 };
    const colW = (w - margin.l - margin.r) / 2;
    const years = [...new Set(matches.map((m) => m.year))].sort();

    teams.forEach((team, ti) => {
      const teamMatches = matches.filter((m) => m.team === team).sort((a, b) => a.date.localeCompare(b.date));
      const cx = margin.l + colW * ti + colW / 2;
      const maxGd = Math.max(4, ...teamMatches.map((m) => Math.abs(m.gd)), 1);
      const scale = (colW * 0.4) / maxGd;

      ctx.strokeStyle = '#3a5040';
      ctx.beginPath();
      ctx.moveTo(cx, margin.t);
      ctx.lineTo(cx, h - margin.b);
      ctx.stroke();

      ctx.fillStyle = '#8ab098';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(team, cx, 12);

      teamMatches.forEach((m, i) => {
        const y = margin.t + 20 + i * 18;
        const x2 = cx + m.gd * scale;
        ctx.strokeStyle = m.ko ? KO_KNOCK : KO_GROUP;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, y);
        ctx.lineTo(x2, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x2, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#122018';
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#6a8f72';
        ctx.font = '8px sans-serif';
        ctx.textAlign = ti === 0 ? 'right' : 'left';
        ctx.fillText(m.year + ' (' + (m.gd > 0 ? '+' : '') + m.gd + ')', ti === 0 ? cx - 6 : cx + 6, y + 3);
      });
    });
  }

  function drawScoreHeatmap(canvas, teamA, teamB, rates) {
    const ra = rates[teamA] || { gf: 1.2, ga: 1.0 };
    const rb = rates[teamB] || { gf: 1.2, ga: 1.0 };
    const la = ra.gf;
    const lb = rb.gf;
    const maxG = 5;
    const grid = [];
    let maxP = 0;
    for (let i = 0; i <= maxG; i++) {
      for (let j = 0; j <= maxG; j++) {
        const p = poisson(i, la) * poisson(j, lb);
        grid.push({ i, j, p });
        if (p > maxP) maxP = p;
      }
    }
    let pWinA = 0, pDraw = 0, pWinB = 0;
    grid.forEach(({ i, j, p }) => {
      if (i > j) pWinA += p;
      else if (i < j) pWinB += p;
      else pDraw += p;
    });

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const wrap = canvas.parentElement;
    const size = Math.max(280, (wrap?.clientWidth || 360) - 20);
    canvas.width = size * dpr;
    canvas.height = (size + 44) * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = (size + 44) + 'px';
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#122018';
    ctx.fillRect(0, 0, size, size + 44);

    const barY = 4;
    const barH = 10;
    const barW = size - 20;
    const x0 = 10;
    ctx.fillStyle = '#3a8fd8';
    ctx.fillRect(x0, barY, barW * pWinA, barH);
    ctx.fillStyle = '#6a8f72';
    ctx.fillRect(x0 + barW * pWinA, barY, barW * pDraw, barH);
    ctx.fillStyle = '#d64040';
    ctx.fillRect(x0 + barW * (pWinA + pDraw), barY, barW * pWinB, barH);
    ctx.fillStyle = '#8ab098';
    ctx.font = '8px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(teamA + ' ' + (pWinA * 100).toFixed(0) + '%', x0, barY + 22);
    ctx.textAlign = 'right';
    ctx.fillText(teamB + ' ' + (pWinB * 100).toFixed(0) + '%', x0 + barW, barY + 22);
    ctx.textAlign = 'center';
    ctx.fillText('Empate ' + (pDraw * 100).toFixed(0) + '%', x0 + barW / 2, barY + 22);

    const cell = Math.max(28, Math.floor((size - 60) / (maxG + 1)));
    const ox = 30;
    const oy = 50;
    grid.forEach(({ i, j, p }) => {
      const t = p / maxP;
      let color;
      if (i > j) color = `rgba(58,143,216,${0.15 + t * 0.85})`;
      else if (i < j) color = `rgba(214,64,64,${0.15 + t * 0.85})`;
      else color = `rgba(138,176,152,${0.15 + t * 0.85})`;
      ctx.fillStyle = color;
      ctx.fillRect(ox + j * cell, oy + (maxG - i) * cell, cell - 2, cell - 2);
      if (t > 0.55) {
        ctx.fillStyle = '#fff';
        ctx.font = '8px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText((p * 100).toFixed(0) + '%', ox + j * cell + cell / 2, oy + (maxG - i) * cell + cell / 2 + 3);
      }
    });
    ctx.fillStyle = '#6a8f72';
    ctx.font = '9px sans-serif';
    ctx.fillText('Gols ' + teamB, ox + (maxG * cell) / 2, oy + maxG * cell + 24);
    ctx.save();
    ctx.translate(12, oy + (maxG * cell) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Gols ' + teamA, 0, 0);
    ctx.restore();
  }

  function renderAdvancedViz(VIZ_DATA, STATS_EXTRA, f, charts) {
    if (!VIZ_DATA) return;
    const gk = genderKey(f);

    const mr = pickBucket(VIZ_DATA.match_results, f);
    const heatCanvas = document.getElementById('c-match-results');
    if (heatCanvas) drawMatchResultsHeatmap(heatCanvas, mr, f.team || '');

    const pen = pickBucket(VIZ_DATA.penalties, f);
    if (charts.penalties) {
      renderPenaltiesChart(charts.penalties, pen);
    }

    const uefa = VIZ_DATA.goals_by_conf.UEFA[gk] || VIZ_DATA.goals_by_conf.UEFA.all;
    const conmebol = VIZ_DATA.goals_by_conf.CONMEBOL[gk] || VIZ_DATA.goals_by_conf.CONMEBOL.all;
    if (charts.uefa) renderConfGoalsChart(charts.uefa, uefa, 'UEFA', '#3a8fd8');
    if (charts.conmebol) renderConfGoalsChart(charts.conmebol, conmebol, 'CONMEBOL', '#2d9c52');

    const h2hSection = document.getElementById('h2h-section');
    const teamA = f.team;
    const teamB = document.getElementById('sel-compare')?.value || '';
    if (!teamA || !teamB || teamA === teamB) {
      if (h2hSection) h2hSection.hidden = true;
      return;
    }
    if (h2hSection) h2hSection.hidden = false;
    document.getElementById('h2h-title').textContent = teamA + ' × ' + teamB;

    const events = pickBucket(VIZ_DATA.h2h, f);
    const h2h = filterH2H(events, teamA, teamB);
    const teams = [teamA, teamB];

    const goalPts = h2h.goals.map((g) => ({
      team: g[0], minute: g[2], ko: g[3], og: g[4], pen: g[5],
    }));
    drawMinuteScatter(document.getElementById('c-h2h-goals'), goalPts, teams, 'goals');

    const matchPts = h2h.matches.map((m) => ({
      team: m[0], year: m[2], gd: m[3], ko: m[4], date: m[5],
    }));
    drawLollipop(document.getElementById('c-h2h-matches'), matchPts, teams);

    const cardPts = h2h.bookings.map((b) => ({
      team: b[0], minute: b[2], ko: b[3], type: b[4],
    }));
    drawMinuteScatter(document.getElementById('c-h2h-cards'), cardPts, teams, 'cards');

    const rates = pickBucket(VIZ_DATA.goal_rates, f);
    drawScoreHeatmap(document.getElementById('c-h2h-probs'), teamA, teamB, rates);
  }

  global.DashboardViz = { renderAdvancedViz, genderKey };
})(window);
