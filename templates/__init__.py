"""
Şablon Sistemi — Plugin Registry
==================================
Yeni şablon eklemek için templates/ klasörüne bir modül eklemek yeterlidir.
Modül, BaseTemplate'ten türeyen bir sınıf içermelidir.
"""

from __future__ import annotations

from templates.base import BaseTemplate
from templates.general import GeneralTemplate

# Şablon kayıt defteri — yeni şablonlar buraya eklenir
_REGISTRY: dict[str, type[BaseTemplate]] = {
    "general": GeneralTemplate,
}


def get_template(name: str) -> BaseTemplate:
    """Şablon adına göre bir şablon örneği döndürür."""
    template_cls = _REGISTRY.get(name)
    if template_cls is None:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Bilinmeyen şablon: '{name}'. Mevcut şablonlar: {available}"
        )
    return template_cls()


def available_templates() -> list[str]:
    """Kullanılabilir şablon adlarını döndürür."""
    return sorted(_REGISTRY.keys())
