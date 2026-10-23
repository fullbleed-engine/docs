"""A kit with concrete defaults and an immutable, per-kit palette."""
from dataclasses import dataclass

from fullbleed.components import Card, Paragraph, component, pt, styled


@dataclass(frozen=True)
class BillingPalette:
    accent: str = "#315b93"
    surface: str = "#edf2f9"
    ink: str = "#20364d"


def billing_kit(palette=BillingPalette()):
    """Return a reusable component; no document theme is required."""
    Panel = styled(Card, background=palette.surface, border="none",
                   border_radius=pt(0), padding=pt(20))
    Label = styled(Paragraph, color=palette.ink, font_size=pt(9),
                   font_weight=700, margin=pt(0))
    Amount = styled(Paragraph, color=palette.accent, font_size=pt(34),
                    font_weight=700, line_height=1.1, margin=(pt(12), pt(0)))
    Note = styled(Paragraph, color=palette.ink, font_size=pt(9), margin=pt(0))

    @component(parts=("label", "amount", "note"))
    def Balance(label, amount, note):
        return Panel(Label(label, part="label"), Amount(amount, part="amount"),
                     Note(note, part="note"), class_name="billing-summary")

    return Balance
