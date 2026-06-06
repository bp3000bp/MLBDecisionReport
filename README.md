# MLB Decision Report

Run-expectancy grading of in-game baseball decisions. v1: Send/Hold Grader — third-base coach decisions on extra-base opportunities, 2020–2024.

## What this is

For every opportunity where a runner on second base could attempt to score on an outfield hit, we estimate the probability the runner would be safe, compute the break-even probability from RE24, and grade the actual coach decision (send / hold) against it.

**Key finding:** In all 18 situational bins, empirical P(safe) ≥ 0.947 exceeds the maximum break-even probability of 0.914. Every run lost came from holding too often — not from sending at the wrong time.

External validation: Spearman ρ = +0.780 (p < 0.0001) vs. Baseball Reference XBT%.

## Architecture

```
/data/reference/    # small committed reference CSVs (coaches, RE24, XBT%)
/src/
  /ingest/          # Statcast + sprint speed + arm strength pulls
  /features/        # opportunity identification, feature engineering
  /model/           # P(safe) model + RE24 + grading
  /eval/            # leaderboards, sanity checks
/scripts/           # build_web_data.py — converts processed CSVs -> web JSON
/web/               # Next.js 16 app (App Router, TypeScript, Tailwind)
  /app/             # pages + API routes
  /components/      # reusable UI
  /lib/             # module system, data access
  /data/            # pre-built JSON served by API routes
```

## Running locally

### Python pipeline
```bash
pip install pybaseball pandas scikit-learn scipy
python -m src.features.opportunities
python -m src.model.re24
python -m src.model.psafe
python -m src.model.grade
python -m src.eval.leaderboards
python scripts/build_web_data.py
```

### Web app
```bash
cd web
npm install
npm run dev
# → http://localhost:3000
```

## Data sources

- **Statcast**: MLB event-level data via pybaseball (2020–2024)
- **Sprint speed**: Baseball Savant via pybaseball
- **Arm strength**: Baseball Savant leaderboard CSV (2020+ only)
- **Run expectancy**: Computed from 2020–2024 Statcast data
- **Coach attribution**: Baseball Reference, manually compiled
- **XBT% validation**: Baseball Reference team baserunning pages
