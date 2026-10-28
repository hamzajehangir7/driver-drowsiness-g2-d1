# Contribution workflow

## Branches
- `main` — stable. Must always run (`python run.py`). Changed only through reviewed pull requests.
- `sgN/<short-topic>` — sub-group work, e.g. `sg4/week5-temporal-windows`, `sg2/ear-threshold-study`.
- `integration/<topic>` — SG-6 cross-module changes (folder layout, shared config, Jetson setup).

## Weekly flow
1. Pick or create an issue titled `W5 | SG4 | <task>` with labels `W5`, `SG4`, and a type (`Code`, `Test`, `Research`, `Integration`, `Documentation`). The issue states the expected evidence (commit, results table, README section).
2. Move the item on the Project board: **Backlog → Ready → In progress → In review → Done**. If blocked, add a comment naming the dependency.
3. `git switch -c sg4/<topic>`, make small commits with meaningful messages (`SG-4: add mock cue stream builder`).
4. Open a PR into `main` that says `Closes #<issue>` and lists what was run. At least one other member reviews.
5. Close the issue only when the evidence exists in `main`; unfinished work rolls to the next week with a note.

## Interface rule
Fields listed in `docs/INTERFACES_V1.md` are frozen. Changing one needs agreement from the dependent sub-group, recorded in the PR.

## Data rule
No raw face images or videos in the repository. Commit feature logs (CSV) or small approved samples only.
