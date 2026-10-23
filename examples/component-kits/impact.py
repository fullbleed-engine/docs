"""A kit with explicitly named document-token dependencies."""
from types import MappingProxyType

from fullbleed.components import Card, Paragraph, component, pt, styled, token


# Export every required value. Prefixes are a naming convention, not scopes.
IMPACT_DEFAULTS = MappingProxyType({
    "impact.accent": "#19715e",
    "impact.surface": "#eaf5ef",
    "impact.ink": "#214d40",
})

Panel = styled(Card, background=token("impact.surface"), border="none",
               border_radius=pt(0), padding=pt(20))
Label = styled(Paragraph, color=token("impact.ink"), font_size=pt(9),
               font_weight=700, margin=pt(0))
Value = styled(Paragraph, color=token("impact.accent"), font_size=pt(34),
               font_weight=700, line_height=1.1, margin=(pt(12), pt(0)))
Note = styled(Paragraph, color=token("impact.ink"), font_size=pt(9), margin=pt(0))


@component(parts=("label", "value", "note"))
def Impact(label, value, note):
    return Panel(Label(label, part="label"), Value(value, part="value"),
                 Note(note, part="note"), class_name="impact-summary")
