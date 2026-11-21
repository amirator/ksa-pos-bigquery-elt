"""Render a real pipeline log (docs/run_logs/*.txt) as a terminal-style PNG for the README.
Only START lines are dropped; every other line is printed as logged."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

src, out, title = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
lines = [ln.rstrip() for ln in src.read_text().splitlines() if " START " not in ln and ln.strip()]
lines = [ln if len(ln) <= 118 else ln[:115] + "..." for ln in lines]
h = 0.16 * len(lines) + 0.6
fig = plt.figure(figsize=(11, h), facecolor="#1E1E1E")
fig.text(0.01, 1 - 0.25 / h, title, color="#C8A75B", family="monospace", fontsize=9, va="top", weight="bold")
for i, ln in enumerate(lines):
    color = "#8FD694" if ("PASS" in ln or "OK created" in ln or "DONE" in ln or "successfully" in ln) else "#D4D4D4"
    fig.text(0.01, 1 - (0.5 + 0.16 * i) / h, ln, color=color, family="monospace", fontsize=7, va="top")
fig.savefig(out, dpi=110, facecolor=fig.get_facecolor(), metadata={"Software": None})
print(out, len(lines), "lines")
