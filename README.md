# worldcup.gotech.education

Dashboards de Copa do Mundo — histórico (1930–2022) e ao vivo (2026).

Inspirado em [dottie.pro/dashboard/copa](https://dottie.pro/dashboard/copa) e no dataset [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup).

## Páginas

| Arquivo | Conteúdo | Fonte de dados |
|---------|----------|----------------|
| [`front-end/index.html`](front-end/index.html) | Histórico com filtros globais | CSVs remotos de [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup) |
| [`front-end/worldcup-dashboard.html`](front-end/worldcup-dashboard.html) | Histórico 1930–2022 (KPIs, gráficos, tabela) | `const DB` embutido no HTML |
| [`front-end/worldcup2026-live.html`](front-end/worldcup2026-live.html) | Copa 2026 ao vivo | Snapshot JSON → APIs legado → fallback estático |

## Dados históricos (1930–2022)

Fonte: repositório [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup) (`data-csv/`).

O pacote R local em [`worldcup/`](worldcup/) é o upstream desse dataset (submodule/cópia do projeto original).

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

URL pública (raw):

```
https://raw.githubusercontent.com/luizotavioautomacao/worldcup.gotech.education/main/output/worldcup2026-snapshot.json
```

Gerar localmente:

```bash
make fetch-live
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

`worldcup2026-live.html` tenta carregar o snapshot nesta ordem:

1. `../output/worldcup2026-snapshot.json` (dev local)
2. `/output/worldcup2026-snapshot.json` (mesmo domínio)
3. Raw do GitHub

Se o snapshot falhar ou estiver com mais de 65 min, cai no fallback: kickoff26 + ESPN no browser, depois JSON estático embutido.

Auto-refresh no browser: **a cada 30 minutos**.

## Desenvolvimento local

```bash
# Servir os HTMLs (snapshot relativo funciona assim)
python3 -m http.server 8000

# Abrir no navegador
# http://localhost:8000/front-end/worldcup2026-live.html
# http://localhost:8000/front-end/worldcup-dashboard.html
# http://localhost:8000/front-end/index.html
```

Abrir via `file://` não carrega o snapshot local; nesse caso o live usa raw GitHub ou fallback.

## Estrutura

```
front-end/              # dashboards HTML
scripts/                # fetcher Python (Copa 2026)
output/                 # snapshot JSON publicado
.github/workflows/      # cron + commit do snapshot
worldcup/               # pacote R / dataset histórico (jfjelstul)
.plans/worldcup/        # planos e documentação interna
```

## Documentação interna

- [`.plans/worldcup/plans/2026-06-15--1152.md`](.plans/worldcup/plans/2026-06-15--1152.md) — arquitetura atual (snapshot, workflow, frontend)
