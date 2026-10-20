# SPDX-License-Identifier: MIT
"""Reusable document components and a small theme, with no HTML templates."""
from fullbleed.ui.experimental import (
    Box, Column, DataTable, Paragraph, Stack, Strong, Theme,
    component, mm, pt, style, styled, token,
)
from data import dollars, restock

THEME = Theme(
    {"ink": "#173e35", "muted": "#52665d", "paper": "#edf2e9", "accent": "#a13e1d"},
    text=style(font_family="Inter", font_size=pt(9), line_height=1.4, color=token("ink")),
)
Kicker = styled(Paragraph, font_size=pt(7), font_weight=700,
                letter_spacing=pt(1), text_transform="uppercase", color=token("accent"))
Small = styled(Paragraph, font_size=pt(7.5), color=token("muted"))


@component(parts=("value", "label"))
def Metric(value, label):
    return Box(
        Stack(
            Paragraph(value, part="value", style=style(font_size=pt(26), font_weight=700, line_height=1.15)),
            Small(label, part="label"), gap=pt(5),
        ),
        style=style(background=token("paper"), padding=pt(12)),
    )


@component
def Brand():
    return Paragraph("GRIDLINE / OPERATIONS", style=style(
        font_size=pt(8), font_weight=700, letter_spacing=pt(1), color=token("ink")))


def Ledger(records):
    return DataTable(
        records,
        caption="Product ledger · all values in USD",
        columns=(
            Column("SKU", lambda row: row["sku"], width=mm(23)),
            Column("Product", lambda row: Strong(row["product"])),
            Column("Category", lambda row: row["category"], width=mm(23)),
            Column("Units", lambda row: f'{row["units"]:,}', align="right", width=mm(19)),
            Column("Net sales", lambda row: dollars(row["net_sales_cents"]), align="right", width=mm(30)),
            Column("Last restock", lambda row: restock(row["last_restock"]), width=mm(30)),
        ),
        class_name="ledger",
    ).with_parts(
        caption=style(text_align="left", font_size=pt(10), font_weight=700, margin_bottom=pt(9)),
        header=style(background=token("ink"), color="#ffffff", font_size=pt(7.5), padding=pt(7)),
        cell=style(font_size=pt(8), padding=(pt(6), pt(7)), border_bottom="0.5pt solid #d9e2d7"),
    )
