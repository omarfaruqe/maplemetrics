"""Display helpers that follow the active language: numbers and geography names."""

from django.utils.formats import get_format
from django.utils.translation import pgettext_lazy

GEOGRAPHY_NAMES = {
    "Canada": pgettext_lazy("geography", "Canada"),
    "Newfoundland and Labrador": pgettext_lazy("geography", "Newfoundland and Labrador"),
    "Prince Edward Island": pgettext_lazy("geography", "Prince Edward Island"),
    "Nova Scotia": pgettext_lazy("geography", "Nova Scotia"),
    "New Brunswick": pgettext_lazy("geography", "New Brunswick"),
    "Quebec": pgettext_lazy("geography", "Quebec"),
    "Ontario": pgettext_lazy("geography", "Ontario"),
    "Manitoba": pgettext_lazy("geography", "Manitoba"),
    "Saskatchewan": pgettext_lazy("geography", "Saskatchewan"),
    "Alberta": pgettext_lazy("geography", "Alberta"),
    "British Columbia": pgettext_lazy("geography", "British Columbia"),
}


def geography_name(name: str) -> str:
    """The name as the active language writes it. Data keys stay in English."""
    label = GEOGRAPHY_NAMES.get(name)
    return str(label) if label is not None else name


def number(value: float, decimals: int = 1, *, signed: bool = False) -> str:
    """Format with the active language's decimal separator (a comma in French)."""
    text = f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"
    return text.replace(".", get_format("DECIMAL_SEPARATOR"))
