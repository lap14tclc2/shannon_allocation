"""Optional equity-curve visualisation for the ranking board."""

from __future__ import annotations

import os


def plot_top_equity_curves(
    results,
    output_path: str,
    top_n: int = 10,
) -> bool:
    """Plot NAV curves of the top-N ranked combinations. Returns False if matplotlib unavailable."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"[plot] matplotlib unavailable, skipping chart: {exc}")
        return False

    if not results:
        return False

    plt.figure(figsize=(13, 7))
    for r in sorted(results, key=lambda x: x.final_nav, reverse=True)[:top_n]:
        xs = [d for d, _ in r.nav_history]
        nav = [v for _, v in r.nav_history]
        plt.plot(xs, nav, label=f"{' '.join(r.symbols)[:28]} ({r.final_nav/1e6:.1f}M)")
    plt.title("Top combinations — NAV (VND) over time, ERC + Shannon rebalancing")
    plt.xlabel("Date")
    plt.ylabel("NAV (VND)")
    plt.legend(loc="upper left", fontsize="small", ncol=2)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Saved equity curve chart -> {output_path}")
    return True