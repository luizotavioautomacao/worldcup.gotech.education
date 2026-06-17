# worldcup.gotech.education

Dashboards de Copa do Mundo — histórico (1930–2022) e ao vivo (2026).

Inspirado em [dottie.pro/dashboard/copa](https://dottie.pro/dashboard/copa) e no dataset [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup).

## Páginas

| Arquivo | Conteúdo | Fonte de dados |
|---------|----------|----------------|
| [`front-end/index.html`](front-end/index.html) | Landing page (newsletter + links para os dashboards) | Estático |
| [`front-end/worldcup-dashboard.html`](front-end/worldcup-dashboard.html) | Dashboard histórico (1930–2022) | JSON embutido + [`dashboard-stats-extra.json`](front-end/dashboard-stats-extra.json) + [`dashboard-viz-data.json`](front-end/dashboard-viz-data.json) |
| [`front-end/worldcup2026-live.html`](front-end/worldcup2026-live.html) | Copa 2026 ao vivo | Snapshot GitHub (fetcher) + ESPN opcional (15s) |

Arquivos de apoio do dashboard histórico:

| Arquivo | Uso |
|---------|-----|
| [`front-end/dashboard-viz.js`](front-end/dashboard-viz.js) | Renderização das visualizações avançadas (heatmap, H2H, pênaltis, Poisson) |
| [`front-end/dashboard-stats-extra.json`](front-end/dashboard-stats-extra.json) | Artilheiros por torneio, recordes e KPIs por seleção |
| [`front-end/dashboard-viz-data.json`](front-end/dashboard-viz-data.json) | Dados pré-processados para filtros dinâmicos e gráficos avançados |

## Dados históricos (1930–2022)

Fonte upstream: repositório [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup).

O submodule [`worldcup-r/`](worldcup-r) contém o pacote R e o dataset completo em `data-json/worldcup.json` (e `data-csv/`).

Inicializar submodules:

```bash
make submodules
```

### Gerar stats e visualizações do dashboard

O script [`scripts/build_dashboard_stats.py`](scripts/build_dashboard_stats.py) lê `worldcup-r/data-json/worldcup.json` e gera:

| Saída | Conteúdo |
|-------|----------|
| `front-end/dashboard-stats-extra.json` | Top artilheiros (M/F), recordes em 1 copa, stats por seleção (títulos, vice, 3º, eliminações no mata-mata) |
| `front-end/dashboard-viz-data.json` | Heatmap W/D/L, pênaltis, gols por confederação, confronto direto (H2H), taxas de gols (Poisson), dados exploratórios filtráveis |

Cada bloco é calculado para **all**, **mens** e **womens**.

O script também atualiza o bloco inline `<script id="stats-extra-data">` em `worldcup-dashboard.html`.

Gerar localmente (requer `worldcup-r` inicializado):

```bash
python3 scripts/build_dashboard_stats.py
```


## Dados ao vivo (2026)

### APIs externas (grátis, sem chave)

| Fonte | URL | Uso |
|-------|-----|-----|
| [@kickoff26/data](https://www.npmjs.com/package/@kickoff26/data) v0.2.0 | `https://unpkg.com/@kickoff26/data@0.2.0/data/` | Calendário, seleções, estádios |
| ESPN scoreboard | `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard` | Placares e status (`?dates=YYYYMMDD`) |

### Snapshot JSON

O script [`scripts/fetch_worldcup2026_live.py`](scripts/fetch_worldcup2026_live.py) mescla kickoff26 + ESPN e grava:

```
output/worldcup2026-snapshot.json
```

Campos principais: `updated_at`, `source`, `stats`, `matches`, `teams`, `venues`.

URL pública (raw, branch `main`):

```
https://raw.githubusercontent.com/luizotavioautomacao/worldcup.gotech.education/refs/heads/main/output/worldcup2026-snapshot.json
```

Gerar localmente:

```bash
python3 scripts/fetch_worldcup2026_live.py
```

Testar ESPN e snapshot:

```bash
python3 scripts/test_espn_scoreboard.py
python3 scripts/test_espn_scoreboard.py --team france
```

### GitHub Actions

Workflow: [`.github/workflows/fetch-worldcup2026-live.yml`](.github/workflows/fetch-worldcup2026-live.yml)

| Config | Valor |
|--------|-------|
| Cron | `0 * * * *` — **24× ao dia** (a cada hora UTC) |
| Janela | `2026-06-11` … `2026-07-31` (fora dela, só `workflow_dispatch`) |
| Saída | Commit automático de `output/worldcup2026-snapshot.json` se houver mudança |

Disparo manual: **Actions → Fetch World Cup 2026 live data → Run workflow**.

Em repositório **público**, os minutos do Actions são gratuitos. O job leva ~1–2 min por execução.

### Frontend ao vivo

[`worldcup2026-live.html`](front-end/worldcup2026-live.html) carrega o snapshot nesta ordem:

1. Raw do GitHub (fetcher — URL acima)
2. `../output/worldcup2026-snapshot.json` (dev local)
3. `/output/worldcup2026-snapshot.json` (mesmo domínio, via Rails)

Se o snapshot falhar, cai no fallback: kickoff26 + ESPN no browser, depois JSON estático embutido.

**Modo ao vivo (opcional):** checkbox *Ao vivo (ESPN · 15s)* ou `?live=1` na URL. Com o modo ativo, o snapshot serve de base e a ESPN sobrescreve placares/status a cada **15 segundos**. A preferência fica em `localStorage` (`worldcup2026-live-mode`).

Endpoint ESPN usado no browser:

```
https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard
```

> `fifa.world.2026/scoreboard` retorna HTTP 400 — não usar.

## Desenvolvimento local

### HTML estático (front-end/)

```bash
python3 -m http.server 8000

# http://localhost:8000/front-end/worldcup-dashboard.html
# http://localhost:8000/front-end/worldcup2026-live.html
# http://localhost:8000/front-end/index.html
```

Abrir via `file://` não carrega o snapshot local; nesse caso o live usa raw GitHub ou fallback.

### Fluxo completo (primeira vez)

```bash
make submodules
python3 scripts/build_dashboard_stats.py   # dashboard histórico
python3 scripts/fetch_worldcup2026_live.py  # snapshot Copa 2026 (opcional)
python3 -m http.server 8000
```

## Estrutura

```
.github/workflows/             # cron + commit do snapshot 2026
front-end/                     # dashboards HTML + JSON de stats/viz
scripts/
  build_dashboard_stats.py     # gera JSONs do dashboard histórico
  fetch_worldcup2026_live.py   # gera snapshot Copa 2026 (kickoff26 + ESPN)
  test_espn_scoreboard.py      # smoke test ESPN + snapshot GitHub
output/                        # snapshot JSON publicado (2026)
worldcup-r/                    # submodule — dataset R (jfjelstul/worldcup)
worldcup/                      # submodule — widgets CDN embeddáveis
.plans/                        # planos e documentação interna
```
