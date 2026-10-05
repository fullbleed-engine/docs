"""Rebuild the comparison figure from the published raw summary (matplotlib 3.8.4)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/renderer-comparison'


def main():
    values = json.loads((ASSETS / 'summary.json').read_text())['results']
    entries = {(r['engine'], r['fixture']): r for r in values}
    engines = ['fullbleed', 'weasyprint', 'chromium']
    labels = ['Fullbleed', 'WeasyPrint', 'Chromium']
    colors = ['#126c67', '#af523d', '#465e8e']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'svg.hashsalt': 'fullbleed-renderer-comparison-20261005'})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), constrained_layout=False)
    for ax, key, title, limit in zip(axes, ['cold_ms', 'warm_ms'],
                                    ['Fresh process · 5 samples', 'Warm process · 30 samples'], [1500, 440]):
        for group, fixture in enumerate(['invoice', 'ledger', 'report']):
            for i, (engine, color) in enumerate(zip(engines, colors)):
                item = entries[engine, fixture][key]
                y = group * 4 + i
                ax.barh(y, item['median'], height=.58, color=color, zorder=2)
                ax.errorbar(item['median'], y,
                            xerr=[[item['median'] - item['min']], [item['max'] - item['median']]],
                            color='#243542', linewidth=.85, capsize=2, zorder=3)
                ax.text(item['max'] + limit * .025, y, f"{item['median']:,.1f}",
                        va='center', fontsize=9, color='#172b3b')
        ax.set_yticks([1, 5, 9], ['Invoice', 'Ledger', 'Report'])
        ax.invert_yaxis()
        ax.set_xlim(0, limit)
        ax.set_xlabel('Milliseconds per complete PDF (lower is faster)', labelpad=10)
        ax.set_title(title, loc='left', fontsize=12, pad=16)
        ax.grid(axis='x', color='#e2e8eb', zorder=0)
        ax.tick_params(axis='both', length=0, pad=7)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.suptitle('Same static documents. Different performance tradeoffs.',
                 x=.065, y=.98, ha='left', fontsize=17, color='#172b3b')
    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in colors]
    fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(.06, .925), ncol=3, frameon=False)
    fig.text(.065, .045, 'Bars: medians. Whiskers: full observed ranges. Maintainer-run on one WSL2 host, 2026-10-05.', fontsize=9)
    fig.text(.065, .014, 'Ledger: Fullbleed/WeasyPrint 3 pages; Chromium 4. Versions, PDFs, and raw data: docs.fullbleed.dev/guides/renderer-comparison/', fontsize=8)
    fig.subplots_adjust(left=.08, right=.98, top=.77, bottom=.17, wspace=.28)
    for suffix in ['svg', 'png']:
        fig.savefig(ASSETS / f'latency.{suffix}', dpi=160, metadata={'Date': None} if suffix == 'svg' else {})


if __name__ == '__main__':
    main()
