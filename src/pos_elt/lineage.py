"""Lineage PNG from dbt's manifest.json, without graphviz (networkx multipartite layout)."""
from __future__ import annotations

import json
from pathlib import Path


def draw_lineage(manifest_path: Path, out: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    m = json.loads(manifest_path.read_text())
    g = nx.DiGraph()
    kinds = {}
    for uid, s in m["sources"].items():
        kinds[uid] = "source"
        g.add_node(uid, label=f"{s['source_name']}.{s['name']}")
    for uid, n in m["nodes"].items():
        if n["resource_type"] != "model":
            continue
        kinds[uid] = n["config"]["materialized"]
        g.add_node(uid, label=n["name"])
        for dep in n["depends_on"]["nodes"]:
            if dep in kinds or dep.startswith(("source.", "model.")):
                g.add_edge(dep, uid)
    for uid, e in m.get("exposures", {}).items():
        kinds[uid] = "exposure"
        g.add_node(uid, label=f"exposure: {e['name']}")
        for dep in e["depends_on"]["nodes"]:
            g.add_edge(dep, uid)
    g.remove_nodes_from([n for n in list(g) if n not in kinds])
    for layer, nodes in enumerate(nx.topological_generations(g)):
        for n in sorted(nodes):
            g.nodes[n]["layer"] = layer
    pos = nx.multipartite_layout(g, subset_key="layer")
    colors = {"source": "#C8A75B", "table": "#0B6E4F", "view": "#4C9F70", "exposure": "#7B8794"}
    fig, ax = plt.subplots(figsize=(14, 6))
    nx.draw_networkx_edges(g, pos, ax=ax, arrows=True, edge_color="#9AA5B1", arrowsize=12)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=500, node_color=[colors[kinds[n]] for n in g])
    for n, (x, y) in pos.items():
        ax.text(x, y - 0.06, g.nodes[n]["label"], ha="center", va="top", fontsize=8)
    for k, c in colors.items():
        ax.scatter([], [], color=c, label=k)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=4, title="dbt node")
    ax.set_title("dbt lineage: raw (loaded by Python) -> staging -> marts -> reporting views")
    ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120, metadata={"Software": None})
    plt.close(fig)
    return out
