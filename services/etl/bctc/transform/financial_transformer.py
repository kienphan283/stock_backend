"""
Transformation utilities for BCTC ETL.
"""

from __future__ import annotations

import re
from typing import Dict


def normalize_item_name(name: str) -> str:
    """Convert raw Alpha Vantage keys into friendly names."""
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = name.replace("_", " ")
    return name.title()


def to_camel_case(text: str) -> str:
    if not text:
        return ""
    words = text.replace("/", " ").replace("-", " ").replace("_", " ").split()
    if not words:
        return ""
    first, *rest = words
    camel = first.lower()
    for word in rest:
        camel += word.capitalize()
    return camel


def build_statement_item(line_item: str, periods: Dict[str, float]) -> Dict[str, float]:
    display_name = (
        str(line_item).replace("us-gaap_", "").replace("_", " ").title()
        if line_item
        else ""
    )
    return {
        "name": to_camel_case(str(line_item)),
        "displayName": display_name,
        **periods,
    }

