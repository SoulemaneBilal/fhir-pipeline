"""Catalogue des règles d'altération et d'injection d'erreurs contrôlées.

Fournit le chargement dynamique depuis config/degradation_rules.yaml et
les méthodes de consultation par identifiant, table cible ou colonne.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.degradation.schemas import DegradationRuleConfig

DEFAULT_RULES_PATH = Path("config/degradation_rules.yaml")


class DegradationCatalog:
    """Gestionnaire et registre central des règles d'altération du pipeline."""

    def __init__(
        self,
        rules: list[DegradationRuleConfig] | None = None,
        rules_path: Path | str | None = None,
    ) -> None:
        self._rules_by_id: dict[str, DegradationRuleConfig] = {}
        self._rules_list: list[DegradationRuleConfig] = []

        if rules is not None:
            for rule in rules:
                self._add_rule(rule)
        else:
            path = Path(rules_path) if rules_path is not None else DEFAULT_RULES_PATH
            if path.exists():
                self._load_from_yaml(path)

    def _add_rule(self, rule: DegradationRuleConfig) -> None:
        self._rules_by_id[rule.rule_id] = rule
        self._rules_list.append(rule)

    def _load_from_yaml(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        raw_rules = data.get("rules", [])
        for item in raw_rules:
            if isinstance(item, dict):
                rule = DegradationRuleConfig(**item)
                self._add_rule(rule)

    @property
    def rules(self) -> list[DegradationRuleConfig]:
        """Retourne la liste de toutes les règles cataloguées."""
        return list(self._rules_list)

    def get_rule(self, rule_id: str) -> DegradationRuleConfig | None:
        """Récupère une règle par son identifiant unique (ex. RULE-DATE-001)."""
        return self._rules_by_id.get(rule_id)

    def list_rules(self, category: str | None = None) -> list[DegradationRuleConfig]:
        """Liste les règles, filtrées optionnellement par catégorie."""
        if category is None:
            return list(self._rules_list)
        return [r for r in self._rules_list if r.category == category]

    def get_rules_for_table(self, table_name: str) -> list[DegradationRuleConfig]:
        """Retourne les règles ciblant une table donnée (ou la pseudo-table 'all')."""
        return [
            r for r in self._rules_list if table_name in r.target_tables or "all" in r.target_tables
        ]

    def get_rules_for_column(
        self, table_name: str, column_name: str
    ) -> list[DegradationRuleConfig]:
        """Retourne les règles applicables à une colonne spécifique d'une table."""
        return [
            r
            for r in self.get_rules_for_table(table_name)
            if not r.target_columns or column_name in r.target_columns
        ]


def load_rules_catalog(path: Path | str | None = None) -> DegradationCatalog:
    """Charge le catalogue d'altérations depuis le chemin spécifié ou la configuration par défaut."""
    return DegradationCatalog(rules_path=path)


def load_catalog(path: Path | str | None = None) -> DegradationCatalog:
    """Alias pour load_rules_catalog."""
    return load_rules_catalog(path)
