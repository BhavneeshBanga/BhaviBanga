# game-of-life-contribution-grid

Turns your GitHub contribution graph into the seed generation of Conway's
Game of Life, simulates it evolving for a while, then folds back into your
real grid before looping. Green = your real commits. Cyan = the organism
your commits gave birth to.

## Setup

1. Create a new public repo, e.g. `game-of-life-contribution-grid`.
2. Copy `life_grid.py` into the repo root.
3. Copy `game-of-life.yml` into `.github/workflows/`.
4. Create a **Personal Access Token** (classic, scope `read:user` is enough)
   at github.com/settings/tokens, and add it as a repo secret named
   `GH_PAT` (Settings → Secrets and variables → Actions).
5. Push. The workflow runs automatically once a day, and once manually the
   first time you push to `main` — check the Actions tab to confirm it
   produced `dist/life-grid-light.svg` and `dist/life-grid-dark.svg` on
   an `output` branch.

## Embed in your profile README

```md
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/<you>/game-of-life-contribution-grid/output/life-grid-dark.svg" />
  <img alt="game of life contribution grid" src="https://raw.githubusercontent.com/<you>/game-of-life-contribution-grid/output/life-grid-light.svg" />
</picture>
```

Replace `<you>` with your GitHub username.

## Tuning

Open `life_grid.py` and adjust:
- `GENERATIONS` — how many Game of Life generations to simulate (default 18)
- `LOOP_SECONDS` — total loop duration (default 26s)
- `HOLD_FRAC` — how long it pauses on your real grid before/after evolving
- `SIM_ALIVE_LIGHT` / `SIM_ALIVE_DARK` — the "organism" color, if cyan isn't your thing

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/<username>/game-of-life-contribution-grid/output/life-grid-dark.svg" />
  <img alt="game of life contribution grid" src="https://raw.githubusercontent.com/<username>/game-of-life-contribution-grid/output/life-grid-light.svg" />
</picture>