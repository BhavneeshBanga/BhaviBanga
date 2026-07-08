"""
Conway's Game of Life — GitHub Contribution Grid Animator
-----------------------------------------------------------
Turns your real GitHub contribution graph into the seed generation of
Conway's Game of Life, simulates several generations forward, then
resolves back into your real contribution grid before looping.

Real data   -> green GitHub palette
Simulation  -> cyan "alive cell" palette
This visually separates "your actual commits" from "the organism your
commits gave birth to", which is the whole point of the effect.

Usage:
    GH_USERNAME=<you> GITHUB_TOKEN=<token with read:user> python3 life_grid.py

If GH_USERNAME/GITHUB_TOKEN are not set, a deterministic synthetic demo
grid is used instead (handy for local previews / CI dry-runs).
"""

import os
import sys
import json
import random
import urllib.request

COLS = 52
ROWS = 7
GENERATIONS = 18          # number of simulated Game of Life generations
HOLD_FRAC = 0.08           # fraction of the loop spent "holding" on the real grid
LOOP_SECONDS = 26          # total animation loop duration, in seconds

LEVELS_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
LEVELS_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
SIM_ALIVE_LIGHT = "#00b4d8"
SIM_ALIVE_DARK = "#39e6ff"
SIM_DEAD_LIGHT = LEVELS_LIGHT[0]
SIM_DEAD_DARK = LEVELS_DARK[0]

GITHUB_GRAPHQL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def fetch_contribution_levels(username, token):
    """Fetch the real contribution level grid (ROWS x weeks) from GitHub's GraphQL API."""
    req = urllib.request.Request(
        GITHUB_GRAPHQL,
        data=json.dumps({"query": QUERY, "variables": {"login": username}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "gol-contribution-snake",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = [[0] * len(weeks) for _ in range(ROWS)]
    for col, week in enumerate(weeks):
        for row, day in enumerate(week["contributionDays"]):
            grid[row][col] = LEVEL_MAP.get(day["contributionLevel"], 0)
    return grid


def synthetic_demo_grid(seed=42):
    """Deterministic pseudo-random grid used for local previews when no
    GitHub token/username is available."""
    rng = random.Random(seed)
    grid = [[0] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            p = rng.random()
            if p > 0.72:
                grid[r][c] = rng.choice([1, 1, 2, 2, 3, 4])
    return grid


def step_life(alive, wrap=True):
    """One generation of Conway's Game of Life on a boolean ROWS x COLS grid."""
    new = [[False] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if wrap:
                        rr %= ROWS
                        cc %= COLS
                    elif not (0 <= rr < ROWS and 0 <= cc < COLS):
                        continue
                    if alive[rr][cc]:
                        n += 1
            if alive[r][c]:
                new[r][c] = n in (2, 3)
            else:
                new[r][c] = n == 3
    return new


def run_simulation(levels_grid, generations):
    alive = [[levels_grid[r][c] > 0 for c in range(COLS)] for r in range(ROWS)]
    frames = [alive]
    cur = alive
    for _ in range(generations):
        cur = step_life(cur)
        frames.append(cur)
    return frames


def build_timeline(levels_grid, sim_frames):
    """
    Ordered list of per-cell "frames" for the whole animation:
      real grid (levels) -> N simulated generations (bool) -> real grid again
    Each frame is tagged ('real'|'sim') so the SVG builder knows which
    palette to use.
    """
    timeline = [("real", levels_grid)]
    for g in sim_frames[1:]:  # skip frame 0 of sim (it's just the bool cast of the real grid)
        timeline.append(("sim", g))
    timeline.append(("real", levels_grid))
    return timeline


def color_for(kind, value, r, c, dark):
    if kind == "real":
        level = value[r][c]
        return (LEVELS_DARK if dark else LEVELS_LIGHT)[level]
    alive = value[r][c]
    if dark:
        return SIM_ALIVE_DARK if alive else SIM_DEAD_DARK
    return SIM_ALIVE_LIGHT if alive else SIM_DEAD_LIGHT


def build_svg(timeline, dark=False):
    cell = 11
    gap = 3
    pitch = cell + gap
    pad = 12
    width = pad * 2 + COLS * pitch - gap
    height = pad * 2 + ROWS * pitch - gap

    n_frames = len(timeline)
    hold_end = HOLD_FRAC * 100
    evolve_end = 100 - HOLD_FRAC * 100
    n_evolve = n_frames - 2  # excludes the two 'real' bookend frames

    evolve_points = []
    if n_evolve > 0:
        span = evolve_end - hold_end
        for i in range(n_evolve):
            pct = hold_end + span * (i + 1) / (n_evolve + 1)
            evolve_points.append(pct)

    bg = "#0d1117" if dark else "#ffffff"

    rects = []
    keyframes = []

    for r in range(ROWS):
        for c in range(COLS):
            anim_name = f"c{r}_{c}"
            x = pad + c * pitch
            y = pad + r * pitch

            stops = [
                (0, color_for(*timeline[0], r, c, dark)),
                (hold_end, color_for(*timeline[0], r, c, dark)),
            ]
            for i, pct in enumerate(evolve_points):
                kind, value = timeline[i + 1]
                stops.append((pct, color_for(kind, value, r, c, dark)))
            stops.append((evolve_end, color_for(*timeline[-1], r, c, dark)))
            stops.append((100, color_for(*timeline[-1], r, c, dark)))

            kf = f"@keyframes {anim_name} {{\n"
            for pct, col in stops:
                kf += f"  {pct:.3f}% {{ fill: {col}; }}\n"
            kf += "}"
            keyframes.append(kf)

            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" ry="2" '
                f'style="animation: {anim_name} {LOOP_SECONDS}s ease-in-out infinite;" />'
            )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<style>
rect {{ shape-rendering: geometricPrecision; }}
{chr(10).join(keyframes)}
</style>
<rect x="0" y="0" width="{width}" height="{height}" fill="{bg}" />
{chr(10).join(rects)}
</svg>"""
    return svg

import os
from dotenv import load_dotenv
load_dotenv()

def main():
    username = os.getenv("GH_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    print(username, "\n", token)

    if username and token:
        levels_grid = fetch_contribution_levels(username, token)
    else:
        print("No GH_USERNAME/GITHUB_TOKEN found - generating synthetic demo grid.", file=sys.stderr)
        levels_grid = synthetic_demo_grid()

    sim_frames = run_simulation(levels_grid, GENERATIONS)
    timeline = build_timeline(levels_grid, sim_frames)

    out_dir = "dist"
    os.makedirs(out_dir, exist_ok=True)

    light_svg = build_svg(timeline, dark=False)
    dark_svg = build_svg(timeline, dark=True)

    with open(os.path.join(out_dir, "life-grid-light.svg"), "w") as f:
        f.write(light_svg)
    with open(os.path.join(out_dir, "life-grid-dark.svg"), "w") as f:
        f.write(dark_svg)

    print("Wrote dist/life-grid-light.svg and dist/life-grid-dark.svg")


if __name__ == "__main__":
    main()