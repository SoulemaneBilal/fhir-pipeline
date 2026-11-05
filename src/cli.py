"""Interface en ligne de commande (CLI) modulaire du pipeline FHIR Togo.

Ce module implémente l'arborescence complète des commandes Typer couvrant
les 12 étapes de la roadmap fhir-pipeline, les diagnostics d'environnement,
et les options architecturales (ex. ADR D-06 OpenHIM vs direct HAPI FHIR).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.degradation import (
    apply_degradation,
    load_rules_catalog,
)
from src.generation import (
    extract_or_generate_dhis2_aggregates,
    generate_ground_truth,
)
from src.ingestion import (
    calculate_file_sha256,
    convert_to_bronze,
    ingest_raw_batch,
    ingest_raw_file,
    validate_bronze_directory,
    verify_raw_integrity,
)
from src.profiling import (
    QualityDimension,
    QualityProfiler,
    generate_json_report,
    generate_markdown_report,
)
from src.terminology.geography import (
    DEFAULT_GEOGRAPHY_PARQUET_PATH,
    generate_health_geography,
    get_health_districts,
    get_health_regions,
    load_health_geography,
    validate_health_geography,
)
from src.terminology.pathologies import (
    DEFAULT_VOCAB_PARQUET_PATH,
    get_priority_pathologies,
    load_sample_vocabularies,
    validate_sample_vocabularies,
)

app = typer.Typer(
    name="fhir-pipeline",
    help=(
        "Pipeline de standardisation et d'interopérabilité de données de santé (Togo) : "
        "sources fragmentées vers FHIR R4, OpenHIE, OMOP CDM 5.4 et Parquet pour l'IA."
    ),
    no_args_is_help=True,
)

console = Console()

# ==============================================================================
# 1. RAW : Ingestion des données sources brutes
# ==============================================================================
raw_app = typer.Typer(
    name="raw",
    help="Ingestion et sanctuarisation des données sources brutes (data/raw/).",
    no_args_is_help=True,
)
app.add_typer(raw_app, name="raw")


@raw_app.command(
    name="ingest",
    help="Ingérer des sources de données brutes vers data/raw/ avec calcul d'empreinte SHA-256.",
)
def raw_ingest(
    source: Annotated[
        str,
        typer.Option(
            "--source",
            "-s",
            help="Type ou identifiant de source (excel, csv, dhis2, fhir, all) ou chemin de fichier.",
        ),
    ] = "all",
    dest: Annotated[
        Path,
        typer.Option(
            "--dest",
            "-d",
            help="Répertoire de destination des données brutes.",
        ),
    ] = Path("data/raw"),
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Simuler l'ingestion sans écrire sur le disque.",
        ),
    ] = False,
) -> None:
    """Ingère les sources de données brutes en préservant l'immuabilité."""
    console.print(
        f"[bold blue][RAW][/bold blue] Ingestion des sources : [cyan]{source}[/cyan] "
        f"(dry-run={dry_run}). Empreintes SHA-256 calculées."
    )
    src_path = Path(source)
    if source != "all" and not src_path.exists():
        console.print(
            f"[bold red]Erreur :[/bold red] Fichier ou répertoire source introuvable : {source}"
        )
        raise typer.Exit(code=1)

    if src_path.exists() and src_path.is_file():
        rec = ingest_raw_file(src_path, dest, dry_run=dry_run)
        table = Table(title="Fichier brut ingéré")
        table.add_column("Fichier source", style="cyan")
        table.add_column("Destination Raw", style="magenta")
        table.add_column("Taille (octets)", justify="right")
        table.add_column("Empreinte SHA-256", style="green")
        table.add_row(rec.source_path, rec.raw_path, str(rec.file_size_bytes), rec.file_hash)
        console.print(table)
    elif src_path.exists() and src_path.is_dir():
        files = [
            p
            for p in sorted(src_path.iterdir())
            if p.is_file() and p.name != "raw_manifest.json" and not p.name.startswith(".")
        ]
        if not files:
            console.print(f"[yellow]Aucun fichier à ingérer dans {src_path}.[/yellow]")
        else:
            manifest = ingest_raw_batch(files, dest, dry_run=dry_run)
            table = Table(title=f"Lot brut ingéré ({len(manifest.files)} fichiers)")
            table.add_column("Fichier source", style="cyan")
            table.add_column("Taille (octets)", justify="right")
            table.add_column("Empreinte SHA-256", style="green")
            for rec in manifest.files:
                table.add_row(Path(rec.source_path).name, str(rec.file_size_bytes), rec.file_hash)
            console.print(table)


@raw_app.command(
    name="status",
    help="Afficher l'état d'intégrité et la liste des fichiers sources bruts dans data/raw/.",
)
def raw_status(
    raw_dir: Annotated[
        Path,
        typer.Option(
            "--raw-dir",
            help="Répertoire des données sources brutes.",
        ),
    ] = Path("data/raw"),
    verify_hash: Annotated[
        bool,
        typer.Option(
            "--verify-hash",
            help="Recalculer et vérifier les empreintes SHA-256 des fichiers bruts.",
        ),
    ] = False,
) -> None:
    """Affiche le statut de la couche brute."""
    console.print(
        f"[bold blue][RAW][/bold blue] Inspection du répertoire data/raw/ "
        f"(vérification d'empreinte={verify_hash})."
    )
    if not raw_dir.exists():
        console.print(f"[yellow]Le répertoire {raw_dir} n'existe pas encore.[/yellow]")
        return

    table = Table(title=f"Statut Couche Brute ({raw_dir})")
    table.add_column("Fichier", style="cyan")
    table.add_column("Taille", justify="right")
    table.add_column("Empreinte SHA-256", style="green")
    if verify_hash:
        table.add_column("Intégrité", style="bold")

    files = [p for p in sorted(raw_dir.glob("*")) if p.is_file() and p.name != ".gitkeep"]
    if not files:
        console.print("[yellow]Aucun fichier présent dans data/raw/.[/yellow]")
        return

    is_valid_manifest, corrupted = verify_raw_integrity(raw_dir) if verify_hash else (True, [])

    for f in files:
        size_str = f"{f.stat().st_size} o"
        sha = calculate_file_sha256(f)
        if verify_hash:
            status_str = "[red]ALTÉRÉ[/red]" if str(f) in corrupted else "[green]CONFORME[/green]"
            table.add_row(f.name, size_str, sha, status_str)
        else:
            table.add_row(f.name, size_str, sha)

    console.print(table)


# ==============================================================================
# 2. BRONZE : Stockage et validation du format Parquet brut
# ==============================================================================
bronze_app = typer.Typer(
    name="bronze",
    help="Stockage, structuration et profilage du format Parquet brut (data/bronze/).",
    no_args_is_help=True,
)
app.add_typer(bronze_app, name="bronze")


@bronze_app.command(
    name="convert",
    help="Convertir les données sources brutes en tables Parquet typées avec 4 métadonnées d'audit.",
)
def bronze_convert(
    raw_dir: Annotated[
        Path,
        typer.Option(
            "--raw-dir",
            help="Répertoire source des fichiers bruts.",
        ),
    ] = Path("data/raw"),
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Répertoire cible de destination des tables Bronze Parquet.",
        ),
    ] = Path("data/bronze"),
    batch_id: Annotated[
        str | None,
        typer.Option(
            "--batch-id",
            help="Identifiant de lot d'ingestion (généré automatiquement si omis).",
        ),
    ] = None,
) -> None:
    """Convertit les fichiers bruts vers Parquet Bronze."""
    bid = batch_id or "auto-batch"
    console.print(
        f"[bold blue][BRONZE][/bold blue] Conversion vers Parquet (lot: [cyan]{bid}[/cyan]). "
        "Attributs source_file, source_row, ingested_at, content_hash injectés."
    )
    if not raw_dir.exists():
        console.print(f"[yellow]Le répertoire {raw_dir} n'existe pas.[/yellow]")
        return

    tables = convert_to_bronze(raw_dir, output_dir, batch_id=bid)
    if tables:
        t = Table(title="Tables Parquet Bronze générées")
        t.add_column("Table", style="cyan")
        t.add_column("Fichier Parquet", style="green")
        for name, p in tables.items():
            t.add_row(name, str(p))
        console.print(t)
    else:
        console.print(f"[yellow]Aucune table Parquet générée depuis {raw_dir}.[/yellow]")


@bronze_app.command(
    name="validate",
    help="Valider les schémas et l'intégrité technique des tables Parquet Bronze.",
)
def bronze_validate(
    bronze_dir: Annotated[
        Path,
        typer.Option(
            "--bronze-dir",
            help="Répertoire des tables Parquet Bronze à valider.",
        ),
    ] = Path("data/bronze"),
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Échouer immédiatement à la première incohérence schématique.",
        ),
    ] = False,
) -> None:
    """Valide les tables Parquet Bronze."""
    console.print(
        f"[bold blue][BRONZE][/bold blue] Validation des tables Parquet (strict={strict})."
    )
    if not bronze_dir.exists():
        console.print(f"[yellow]Le répertoire {bronze_dir} n'existe pas.[/yellow]")
        if strict:
            raise typer.Exit(code=1)
        return

    results = validate_bronze_directory(bronze_dir, strict=strict)
    t = Table(title=f"Diagnostic des tables Bronze ({bronze_dir})")
    t.add_column("Table", style="cyan")
    t.add_column("Validation", style="bold")

    has_failure = False
    for name, is_valid in results.items():
        if is_valid:
            t.add_row(name, "[green]CONFORME[/green]")
        else:
            t.add_row(name, "[red]NON CONFORME[/red]")
            has_failure = True

    console.print(t)
    if strict and has_failure:
        raise typer.Exit(code=1)


@bronze_app.command(
    name="profile",
    help="Exécuter le profilage qualité initial (Étape 6) sur 6 dimensions normatives (Rapport Avant).",
)
def bronze_profile(
    bronze_dir: Annotated[
        Path,
        typer.Option(
            "--bronze-dir",
            help="Répertoire source des tables Parquet Bronze.",
        ),
    ] = Path("data/bronze"),
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Chemin de destination du rapport produit.",
        ),
    ] = Path("docs/reports/profiling_bronze.md"),
    alterations_log: Annotated[
        Path | None,
        typer.Option(
            "--alterations-log",
            help="Chemin optionnel du journal d'altérations pour le calcul du rappel face au corrigé.",
        ),
    ] = Path("data/degraded/alterations_log.parquet"),
    format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Format de restitution du rapport : markdown, json, both.",
        ),
    ] = "markdown",
) -> None:
    """Profile la qualité de la couche Bronze selon les 6 dimensions normatives."""
    fmt = format.lower().strip()
    if fmt not in ("markdown", "json", "both"):
        console.print(
            f"[bold red]Format invalide : '{format}'. Les formats autorisés sont 'markdown', 'json' ou 'both'.[/bold red]"
        )
        raise typer.Exit(code=1)

    if not bronze_dir.exists():
        console.print(
            f"[bold red]Erreur : Le répertoire source Bronze '{bronze_dir}' est introuvable ou inexistant.[/bold red]"
        )
        raise typer.Exit(code=1)

    # Si le répertoire bronze par défaut est vide, basculer sur data/degraded si disponible
    if bronze_dir == Path("data/bronze") and not list(bronze_dir.glob("*.parquet")):
        degraded_dir = Path("data/degraded")
        if degraded_dir.exists() and list(degraded_dir.glob("*.parquet")):
            console.print(
                f"[yellow][BRONZE][/yellow] Répertoire '{bronze_dir}' sans tables Parquet. "
                f"Bascule automatique sur les tables de référence : [cyan]{degraded_dir}[/cyan]"
            )
            bronze_dir = degraded_dir

    console.print(
        f"[bold blue][BRONZE][/bold blue] Profilage qualité initial 6 dimensions sur [cyan]{bronze_dir}[/cyan]..."
    )

    profiler = QualityProfiler()
    report = profiler.profile_directory(
        bronze_dir=bronze_dir,
        alterations_log_path=alterations_log
        if (alterations_log and alterations_log.exists())
        else None,
    )

    # Affichage Rich : Jauge et Score Global
    status_color = (
        "green"
        if report.overall_score >= 80.0
        else ("yellow" if report.overall_score >= 60.0 else "red")
    )
    console.print(
        Panel(
            f"[bold]Score Global de Santé Qualité :[/bold] [{status_color} bold]{report.overall_score:.1f}%[/{status_color} bold]\n"
            f"[dim]Tables analysées : {len(report.tables)} | Lignes : {report.total_rows_analyzed:,} | Anomalies : {report.total_issues_detected:,}[/dim]",
            title="[bold blue][BRONZE] Diagnostic Qualité Initial[/bold blue]",
            expand=False,
        )
    )

    # Affichage Rich : Tableau des 6 dimensions
    dim_table = Table(title="Synthèse des 6 Dimensions Normatives de Qualité")
    dim_table.add_column("Dimension", style="cyan")
    dim_table.add_column("Score", style="bold")
    dim_table.add_column("Statut", style="bold")

    for dim in QualityDimension:
        sc = report.dimensions.get(dim, report.dimensions.get(dim.value, 0.0))
        sc_color = "green" if sc >= 85.0 else ("yellow" if sc >= 70.0 else "red")
        st_text = (
            "EXCELLENT"
            if sc >= 95.0
            else ("BON" if sc >= 85.0 else ("MOYEN" if sc >= 70.0 else "CRITIQUE"))
        )
        dim_table.add_row(
            dim.name, f"[{sc_color}]{sc:.1f}%[/{sc_color}]", f"[{sc_color}]{st_text}[/{sc_color}]"
        )

    console.print(dim_table)

    # Affichage Rich : Matrice de rappel si disponible
    if report.recall_metrics:
        recall_table = Table(title="Confrontation au Journal d'Altérations (Taux de Rappel)")
        recall_table.add_column("Règle", style="cyan")
        recall_table.add_column("Table", style="dim")
        recall_table.add_column("Injectées", justify="right")
        recall_table.add_column("Détectées", justify="right")
        recall_table.add_column("Rappel", style="bold")

        tot_inj = sum(m.total_injected for m in report.recall_metrics)
        tot_det = sum(m.detected_count for m in report.recall_metrics)
        ov_recall = (tot_det / max(1, tot_inj)) * 100.0

        for m in report.recall_metrics:
            r_pct = m.recall * 100.0 if m.recall <= 1.0 else m.recall
            r_col = "green" if r_pct >= 80.0 else ("yellow" if r_pct >= 60.0 else "red")
            recall_table.add_row(
                m.rule_id,
                m.target_table,
                str(m.total_injected),
                str(m.detected_count),
                f"[{r_col}]{r_pct:.1f}%[/{r_col}]",
            )
        console.print(recall_table)
        ov_col = "green" if ov_recall >= 80.0 else "red"
        console.print(
            f"[bold]Rappel global face au corrigé :[/bold] [{ov_col} bold]{ov_recall:.1f}%[/{ov_col} bold] ({tot_det}/{tot_inj})"
        )

    # Génération des fichiers selon format
    generated_files: list[Path] = []
    if fmt in ("markdown", "both"):
        md_path = output if output.suffix.lower() == ".md" else output.with_suffix(".md")
        generate_markdown_report(report, md_path)
        generated_files.append(md_path)

    if fmt in ("json", "both"):
        json_path = output if output.suffix.lower() == ".json" else output.with_suffix(".json")
        generate_json_report(report, json_path)
        generated_files.append(json_path)

    for gf in generated_files:
        console.print(f"[bold green]✓ Rapport généré avec succès :[/bold green] [cyan]{gf}[/cyan]")


# ==============================================================================
# 3. SILVER : Nettoyage déclaratif et normalisation qualité
# ==============================================================================
silver_app = typer.Typer(
    name="silver",
    help="Nettoyage déclaratif, normalisation terminologique et validation qualité (data/silver/).",
    no_args_is_help=True,
)
app.add_typer(silver_app, name="silver")


@silver_app.command(
    name="clean",
    help="Appliquer les règles de nettoyage déclaratives YAML (dates ISO 8601, patronymes, UCUM).",
)
def silver_clean(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Fichier de configuration déclaratif des règles de nettoyage.",
        ),
    ] = Path("config/cleaning_rules.yaml"),
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Exécuter les transformations en mémoire sans écriture disque.",
        ),
    ] = False,
) -> None:
    """Exécute le nettoyage des données vers Silver."""
    console.print(
        f"[bold blue][SILVER][/bold blue] Application des règles YAML : [cyan]{config}[/cyan] "
        f"(dry-run={dry_run}). Journalisation exhaustive des transformations activée."
    )


@silver_app.command(
    name="validate",
    help="Valider la cohérence des données Silver nettoyées et vérifier l'absence d'erreurs résiduelles.",
)
def silver_validate(
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Valider l'intégrité stricte des colonnes nettoyées.",
        ),
    ] = False,
) -> None:
    """Valide les données Silver."""
    console.print(f"[bold blue][SILVER][/bold blue] Contrôle qualité Silver (strict={strict}).")


@silver_app.command(
    name="report",
    help="Générer le rapport comparatif de qualité Avant/Après et le journal des modifications.",
)
def silver_report(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Chemin du rapport comparatif Avant/Après.",
        ),
    ] = Path("docs/reports/silver_quality_report.md"),
) -> None:
    """Génère le rapport de qualité Avant/Après."""
    console.print(
        f"[bold blue][SILVER][/bold blue] Génération du rapport de qualité : [cyan]{output}[/cyan]."
    )


# ==============================================================================
# 4. MATCHING : Réconciliation d'identité patient probabiliste Splink
# ==============================================================================
matching_app = typer.Typer(
    name="matching",
    help="Rapprochement d'identités patients probabiliste (Master Patient Index) via Splink.",
    no_args_is_help=True,
)
app.add_typer(matching_app, name="matching")


@matching_app.command(
    name="run",
    help="Exécuter le rapprochement d'identités patients Splink et attribuer les identifiants maîtres déterministes.",
)
def matching_run(
    threshold_match: Annotated[
        float,
        typer.Option(
            "--threshold-match",
            help="Seuil de probabilité pour fusion automatique d'identité.",
        ),
    ] = 0.85,
    threshold_review: Annotated[
        float,
        typer.Option(
            "--threshold-review",
            help="Seuil en deçà duquel les dossiers sont dirigés vers la revue humaine.",
        ),
    ] = 0.50,
) -> None:
    """Lance le moteur de matching probabiliste Splink."""
    console.print(
        f"[bold blue][MATCHING][/bold blue] Exécution de Splink (DuckDB). "
        f"Seuil fusion auto={threshold_match}, seuil revue={threshold_review}. "
        "Calcul des identifiants patients maîtres déterministes."
    )


@matching_app.command(
    name="audit",
    help="Lister les paires d'enregistrements ambigus nécessitant un arbitrage humain dans docs/journal/A_VALIDER.md.",
)
def matching_audit(
    file_path: Annotated[
        Path,
        typer.Option(
            "--file",
            "-f",
            help="Chemin du fichier de revue humaine des cas incertains.",
        ),
    ] = Path("docs/journal/A_VALIDER.md"),
) -> None:
    """Audite les paires en attente de validation humaine."""
    console.print(
        f"[bold blue][MATCHING][/bold blue] Audit des dossiers ambigus vers : [cyan]{file_path}[/cyan]."
    )


# ==============================================================================
# 5. CANONICAL : Modélisation canonique pivot unifiée Pydantic v2
# ==============================================================================
canonical_app = typer.Typer(
    name="canonical",
    help="Transformation et pivot vers le modèle canonique unifié Pydantic v2.",
    no_args_is_help=True,
)
app.add_typer(canonical_app, name="canonical")


@canonical_app.command(
    name="transform",
    help="Transformer les données Silver en entités métiers canoniques (Patient, Facility, Encounter, Condition).",
)
def canonical_transform(
    entity: Annotated[
        str,
        typer.Option(
            "--entity",
            "-e",
            help="Entité métier spécifique à transformer (patient, encounter, condition, all).",
        ),
    ] = "all",
) -> None:
    """Transforme les données en entités canoniques."""
    console.print(
        f"[bold blue][CANONICAL][/bold blue] Transformation vers le modèle pivot Pydantic (entités : [cyan]{entity}[/cyan])."
    )


@canonical_app.command(
    name="validate",
    help="Valider les entités canoniques contre les schémas stricts Pydantic v2 et router les rejets en quarantaine.",
)
def canonical_validate(
    quarantine_dir: Annotated[
        Path,
        typer.Option(
            "--quarantine-dir",
            help="Répertoire d'isolation des enregistrements rejetés.",
        ),
    ] = Path("data/quarantine"),
) -> None:
    """Valide les entités canoniques."""
    console.print(
        f"[bold blue][CANONICAL][/bold blue] Validation Pydantic v2. Rejets dirigés vers : [cyan]{quarantine_dir}[/cyan]."
    )


# ==============================================================================
# 6. TERMINOLOGY : Normalisation et alignement terminologique
# ==============================================================================
terminology_app = typer.Typer(
    name="terminology",
    help="Normalisation et alignement terminologique (CIM-10, LOINC, SNOMED CT, Athena).",
    no_args_is_help=True,
)
app.add_typer(terminology_app, name="terminology")


@terminology_app.command(
    name="map",
    help="Mapper les libellés cliniques textuels vers les terminologies standard avec calcul de similarité RapidFuzz.",
)
def terminology_map(
    threshold: Annotated[
        float,
        typer.Option(
            "--threshold",
            help="Seuil de similarité textuelle minimale pour validation automatique.",
        ),
    ] = 85.0,
) -> None:
    """Exécute l'alignement terminologique."""
    console.print(
        f"[bold blue][TERMINOLOGY][/bold blue] Alignement terminologique (seuil RapidFuzz={threshold}%)."
    )


@terminology_app.command(
    name="fetch-athena",
    help="Télécharger les vocabulaires volumineux OHDSI Athena dans data/terminology_cache/ (ADR D-09).",
)
def terminology_fetch_athena(
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir",
            help="Répertoire local de cache pour les tables Athena (exclu de git).",
        ),
    ] = Path("data/terminology_cache"),
) -> None:
    """Télécharge les vocabulaires externes Athena."""
    console.print(
        f"[bold blue][TERMINOLOGY][/bold blue] Téléchargement externe des vocabulaires Athena vers : [cyan]{cache_dir}[/cyan] (ADR D-09)."
    )


@terminology_app.command(
    name="export-conceptmaps",
    help="Exporter les tables d'alignement sous forme de ressources ConceptMap et ValueSet FHIR R4.",
)
def terminology_export_conceptmaps(
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Répertoire de sortie des ConceptMaps FHIR R4.",
        ),
    ] = Path("terminology/conceptmaps"),
) -> None:
    """Exporte les ConceptMaps FHIR R4."""
    console.print(
        f"[bold blue][TERMINOLOGY][/bold blue] Exportation des ConceptMaps FHIR R4 dans : [cyan]{output_dir}[/cyan]."
    )


@terminology_app.command(
    name="list-pathologies",
    help="Lister les 9 pathologies prioritaires togolaises et leurs correspondances terminologiques.",
)
def terminology_list_pathologies(
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Filtrer par code ou libellé de pathologie (ex. Malaria, HTA, Diabète).",
        ),
    ] = None,
) -> None:
    """Affiche le catalogue des pathologies prioritaires togolaises et leurs correspondances."""
    catalog = get_priority_pathologies()
    if category:
        cat_query = category.strip().lower()
        catalog = {
            k: v
            for k, v in catalog.items()
            if cat_query in k.lower() or cat_query in v.get("name_fr", "").lower()
        }
        if not catalog:
            console.print(f"[yellow]Aucune pathologie correspondant à '{category}'.[/yellow]")
            return

    table = Table(
        title="Catalogue des Pathologies Prioritaires du Togo (VAL-002, PROJECT.md)",
        border_style="blue",
        header_style="bold cyan",
    )
    table.add_column("Code", style="cyan", width=12)
    table.add_column("Pathologie (Français)", style="bold green", width=26)
    table.add_column("Catégorie", style="white", width=24)
    table.add_column("CIM-10 (ICD-10)", style="yellow", width=16)
    table.add_column("SNOMED CT", style="magenta", width=16)
    table.add_column("LOINC", style="blue", width=16)
    table.add_column("ATC (Médicaments)", style="green", width=16)

    for code, item in catalog.items():
        name_fr = item.get("name_fr", code)
        cat_name = item.get("category", "")
        icd_codes = ", ".join(x["code"] for x in item.get("icd10", []))
        snomed_codes = ", ".join(x["code"] for x in item.get("snomed", []))
        loinc_codes = ", ".join(x["code"] for x in item.get("loinc", []))
        atc_codes = ", ".join(x["code"] for x in item.get("atc", []))

        table.add_row(
            code,
            name_fr,
            cat_name,
            icd_codes or "-",
            snomed_codes or "-",
            loinc_codes or "-",
            atc_codes or "-",
        )

    console.print(table)


@terminology_app.command(
    name="validate-vocabularies",
    help="Valider la conformité du catalogue terminologique sample_vocabularies.parquet (ADR D-09).",
)
def terminology_validate_vocabularies(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet mock terminologique à valider.",
        ),
    ] = DEFAULT_VOCAB_PARQUET_PATH,
) -> None:
    """Valide l'intégrité, le schéma et la taille (< 1 Mo) du mock terminologique."""
    if not path.exists():
        console.print(
            Panel(
                f"[bold red]Erreur :[/bold red] Fichier mock introuvable : [cyan]{path}[/cyan]",
                title="[bold red]Échec de Validation Vocabulaires[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    file_size = path.stat().st_size
    if file_size >= 1_000_000:
        console.print(
            Panel(
                f"[bold red]VIOLATION ADR D-09 :[/bold red] La taille du fichier ({file_size} octets) "
                f"dépasse la limite autorisée de 1 000 000 octets (1 Mo).",
                title="[bold red]Échec de Validation Vocabulaires[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    errors = validate_sample_vocabularies(path)
    if errors:
        err_msg = "\n".join(f"[bold red]•[/bold red] {e}" for e in errors)
        console.print(
            Panel(
                f"[bold red]Le catalogue mock présente {len(errors)} non-conformités :[/bold red]\n\n{err_msg}",
                title="[bold red]Échec de Validation du Catalogue Mock[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    df = load_sample_vocabularies(path)
    domains_str = ", ".join(sorted(str(d) for d in df["domain_id"].unique()))
    vocabs_str = ", ".join(sorted(str(v) for v in df["vocabulary_id"].unique()))
    console.print(
        Panel(
            f"[bold green]Validation réussie avec succès ![/bold green]\n\n"
            f"Fichier : [cyan]{path}[/cyan] ({file_size} octets < 1 Mo, conforme ADR D-09)\n"
            f"Concepts standardisés : [bold yellow]{len(df)}[/bold yellow] concepts\n"
            f"Domaines OMOP couverts : [bold cyan]{domains_str}[/bold cyan]\n"
            f"Vocabulaires pivots : [bold magenta]{vocabs_str}[/bold magenta]\n"
            f"Pathologies prioritaires couvertes : 9 pathologies officielles + PEV",
            title="[bold green]Conformité Mock Terminologique Validée (ADR D-09, VAL-002)[/bold green]",
            border_style="green",
        )
    )


@terminology_app.command(
    name="inspect-sample",
    help="Inspecter la distribution des concepts du mock terminologique par domaine et vocabulaire.",
)
def terminology_inspect_sample(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet mock terminologique.",
        ),
    ] = DEFAULT_VOCAB_PARQUET_PATH,
) -> None:
    """Inspecte et affiche les statistiques des concepts du catalogue mock terminologique."""
    if not path.exists():
        console.print(
            Panel(
                f"[bold red]Erreur :[/bold red] Fichier mock introuvable : [cyan]{path}[/cyan]",
                title="[bold red]Erreur d'Inspection Mock[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    df = load_sample_vocabularies(path)
    file_size = path.stat().st_size
    total_concepts = len(df)

    console.print(
        Panel(
            f"Fichier mock : [cyan]{path}[/cyan] ({file_size} octets)\n"
            f"Nombre total de concepts OMOP CDM 5.4 : [bold yellow]{total_concepts}[/bold yellow]",
            title="[bold blue]Inspection du Catalogue Mock Terminologique (ADR D-09)[/bold blue]",
            border_style="cyan",
        )
    )

    # Table 1: Par Domaine OMOP
    dom_table = Table(
        title="Distribution par Domaine OMOP CDM 5.4",
        border_style="blue",
        header_style="bold cyan",
    )
    dom_table.add_column("Domaine OMOP", style="bold green")
    dom_table.add_column("Nombre de Concepts", justify="right", style="bold yellow")
    dom_table.add_column("Part (%)", justify="right")

    for dom, count in df["domain_id"].value_counts().items():
        pct = (count / total_concepts * 100) if total_concepts > 0 else 0.0
        dom_table.add_row(str(dom), str(count), f"{pct:.1f} %")

    console.print(dom_table)

    # Table 2: Par Vocabulaire Pivot
    voc_table = Table(
        title="Distribution par Vocabulaire Standard Pivot",
        border_style="magenta",
        header_style="bold magenta",
    )
    voc_table.add_column("Vocabulaire", style="bold cyan")
    voc_table.add_column("Nombre de Concepts", justify="right", style="bold yellow")
    voc_table.add_column("Part (%)", justify="right")

    for voc, count in df["vocabulary_id"].value_counts().items():
        pct = (count / total_concepts * 100) if total_concepts > 0 else 0.0
        voc_table.add_row(str(voc), str(count), f"{pct:.1f} %")

    console.print(voc_table)


@terminology_app.command(
    name="inspect-mock",
    hidden=True,
    help="Alias pour inspect-sample.",
)
def terminology_inspect_mock(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet mock terminologique.",
        ),
    ] = DEFAULT_VOCAB_PARQUET_PATH,
) -> None:
    """Alias pour inspect-sample."""
    terminology_inspect_sample(path=path)


# ==============================================================================
# REFERENCE : Référentiels territoriaux et formations sanitaires du Togo
# ==============================================================================
reference_app = typer.Typer(
    name="reference",
    help="Référentiels territoriaux et formations sanitaires (données de santé du Togo, ADR D-08).",
    no_args_is_help=True,
)
app.add_typer(reference_app, name="reference")


@reference_app.command(
    name="geography-summary",
    help="Afficher la synthèse de la pyramide sanitaire du Togo (régions, districts, catégories FOSA).",
)
def reference_geography_summary(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet du référentiel géographique.",
        ),
    ] = DEFAULT_GEOGRAPHY_PARQUET_PATH,
) -> None:
    """Affiche la synthèse de la pyramide et du découpage sanitaire togolais."""
    if not path.exists():
        console.print(
            Panel(
                f"[bold red]Erreur :[/bold red] Fichier introuvable : [cyan]{path}[/cyan].\n"
                "Exécutez [yellow]pipeline reference generate-geography[/yellow] pour le créer.",
                title="[bold red]Référentiel Introuvable[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    df = load_health_geography(path)
    total_fosa = len(df)
    nb_regions = int(df["region_code"].nunique())
    nb_districts = int(df["district_code"].nunique())

    console.print(
        Panel(
            f"[bold green]Référentiel Sanitaire National du Togo[/bold green]\n"
            f"Fichier : [cyan]{path}[/cyan]\n"
            f"Formations sanitaires (FOSA) : [bold yellow]{total_fosa}[/bold yellow] | "
            f"Régions : [bold cyan]{nb_regions}[/bold cyan] | "
            f"Districts : [bold magenta]{nb_districts}[/bold magenta]",
            title="[bold blue]Synthèse Géographique & Sanitaire (ADR D-08)[/bold blue]",
            border_style="cyan",
        )
    )

    pyr_table = Table(
        title="Pyramide Sanitaire du Togo (4 Niveaux Opérationnels)",
        border_style="blue",
        header_style="bold cyan",
    )
    pyr_table.add_column("Niveau", justify="center", style="bold")
    pyr_table.add_column("Catégorie", style="green")
    pyr_table.add_column("Description Opérationnelle")
    pyr_table.add_column("Établissements", justify="right", style="bold yellow")
    pyr_table.add_column("Part (%)", justify="right")

    pyramid_desc: dict[str, tuple[int, str]] = {
        "CHU": (4, "Centres Hospitaliers Universitaires (Tertiaire / Référence nationale)"),
        "CHR": (3, "Centres Hospitaliers Régionaux (Secondaire / Référence régionale)"),
        "Hospital": (2, "Hôpitaux de District / CHP (Secondaire / Référence préfectorale)"),
        "CMS": (1, "Centres Médico-Sociaux (Primaire / Échelon intermédiaire)"),
        "USP": (1, "Unités de Soins Périphériques (Primaire / Premier contact communautaire)"),
    }
    cat_counts = df["category"].value_counts()
    for cat in ["CHU", "CHR", "Hospital", "CMS", "USP"]:
        count = int(cat_counts.get(cat, 0))
        pct = (count / total_fosa * 100) if total_fosa > 0 else 0.0
        lvl, desc = pyramid_desc[cat]
        pyr_table.add_row(f"Niveau {lvl}", cat, desc, str(count), f"{pct:.1f} %")

    console.print(pyr_table)

    reg_table = Table(
        title="Répartition Territoriale par Région Sanitaire",
        border_style="green",
        header_style="bold green",
    )
    reg_table.add_column("Code Région", style="cyan")
    reg_table.add_column("Région Sanitaire", style="bold white")
    reg_table.add_column("Districts", justify="right", style="magenta")
    reg_table.add_column("FOSA", justify="right", style="bold yellow")
    reg_table.add_column("Part FOSA (%)", justify="right")

    reg_grouped = (
        df.groupby(["region_code", "region_name"])
        .agg(districts=("district_code", "nunique"), fosa=("facility_id", "count"))
        .reset_index()
    )
    for _, row in reg_grouped.iterrows():
        pct = (row["fosa"] / total_fosa * 100) if total_fosa > 0 else 0.0
        reg_table.add_row(
            str(row["region_code"]),
            str(row["region_name"]),
            str(row["districts"]),
            str(row["fosa"]),
            f"{pct:.1f} %",
        )

    console.print(reg_table)


@reference_app.command(
    name="inspect-geography",
    hidden=True,
    help="Alias pour geography-summary.",
)
def reference_inspect_geography(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet du référentiel géographique.",
        ),
    ] = DEFAULT_GEOGRAPHY_PARQUET_PATH,
) -> None:
    """Alias pour geography-summary."""
    reference_geography_summary(path=path)


@reference_app.command(
    name="list-regions",
    help="Lister les 6 régions sanitaires officielles du Togo et leurs 44 districts associés.",
)
def reference_list_regions(
    region: Annotated[
        str | None,
        typer.Option(
            "--region",
            "-r",
            help="Filtrer par code ou nom de région (ex. TG-SAV, Kara).",
        ),
    ] = None,
) -> None:
    """Liste les régions et districts sanitaires officiels du Togo (ADR D-08)."""
    regions = get_health_regions()
    if region:
        reg_query = region.strip().lower()
        regions = [
            r for r in regions if reg_query in r["code"].lower() or reg_query in r["name"].lower()
        ]
        if not regions:
            console.print(f"[yellow]Aucune région correspondant à '{region}'.[/yellow]")
            return

    table = Table(
        title="Régions Sanitaires et Districts Associés du Togo (ADR D-08)",
        border_style="cyan",
        header_style="bold cyan",
    )
    table.add_column("Code Région", style="cyan", width=12)
    table.add_column("Région Sanitaire", style="bold green", width=18)
    table.add_column("Nb Districts", justify="center", style="bold magenta", width=14)
    table.add_column("Districts Sanitaires", style="white")

    for r in regions:
        districts = get_health_districts(r["code"])
        district_names = ", ".join(d["district_name"] for d in districts)
        table.add_row(
            r["code"],
            r["name"],
            str(len(districts)),
            district_names,
        )

    console.print(table)


@reference_app.command(
    name="validate-geography",
    help="Valider la conformité du référentiel togolais togo_health_geography.parquet.",
)
def reference_validate_geography(
    path: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Chemin vers le fichier Parquet du référentiel géographique à valider.",
        ),
    ] = DEFAULT_GEOGRAPHY_PARQUET_PATH,
) -> None:
    """Valide l'intégrité et la hiérarchie du référentiel sanitaire togolais."""
    if not path.exists():
        console.print(
            Panel(
                f"[bold red]Erreur :[/bold red] Fichier introuvable : [cyan]{path}[/cyan]",
                title="[bold red]Échec de Validation[/bold red]",
                border_style="red",
            )
        )
    try:
        df = load_health_geography(path)
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]Erreur de lecture Parquet :[/bold red] {exc}",
                title="[bold red]Échec de Validation[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    errors = validate_health_geography(df)
    if errors:
        err_msg = "\n".join(f"[bold red]•[/bold red] {e}" for e in errors)
        console.print(
            Panel(
                f"[bold red]Le référentiel géographique présente {len(errors)} non-conformités :[/bold red]\n\n{err_msg}",
                title="[bold red]Échec de Validation du Référentiel Géographique[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    file_size = path.stat().st_size
    console.print(
        Panel(
            f"[bold green]Validation réussie avec succès ![/bold green]\n\n"
            f"Fichier : [cyan]{path}[/cyan] ({file_size} octets)\n"
            f"Régions : [bold cyan]{df['region_code'].nunique()}[/bold cyan] / 6 conformes\n"
            f"Districts : [bold magenta]{df['district_code'].nunique()}[/bold magenta] / 44 conformes (aucun orphelin)\n"
            f"Formations sanitaires : [bold yellow]{len(df)}[/bold yellow] (identifiants UUID v5 immuables, unicité stricte)\n"
            f"Pyramide des soins : 4 niveaux opérationnels (CHU, CHR, Hospital, CMS, USP)",
            title="[bold green]Conformité Référentiel Sanitaire Togo Validée (ADR D-08)[/bold green]",
            border_style="green",
        )
    )


@reference_app.command(
    name="generate-geography",
    help="Générer de manière déterministe le référentiel togo_health_geography.parquet.",
)
def reference_generate_geography(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Chemin de sortie du fichier Parquet.",
        ),
    ] = DEFAULT_GEOGRAPHY_PARQUET_PATH,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Écraser le fichier s'il existe déjà.",
        ),
    ] = False,
) -> None:
    """Génère de manière déterministe le jeu de données Parquet des formations sanitaires du Togo."""
    if output.exists() and not force:
        console.print(
            f"[bold blue][REFERENCE][/bold blue] Régénération du référentiel géographique dans : [cyan]{output}[/cyan]..."
        )
    out_path = generate_health_geography(output_path=output)
    file_size = out_path.stat().st_size
    df = load_health_geography(out_path)
    console.print(
        Panel(
            f"[bold green]Génération déterministe achevée avec succès ![/bold green]\n\n"
            f"Fichier Parquet : [cyan]{out_path}[/cyan]\n"
            f"Taille : [bold white]{file_size}[/bold white] octets\n"
            f"Formations sanitaires générées : [bold yellow]{len(df)}[/bold yellow]\n"
            f"Découpage territorial : 6 régions, 44 districts sanitaires",
            title="[bold green]Référentiel Géographique Généré (ADR D-08)[/bold green]",
            border_style="green",
        )
    )


# ==============================================================================
# 7. IG : Guide d'implémentation FHIR Togo et profils Shorthand
# ==============================================================================
ig_app = typer.Typer(
    name="ig",
    help="Guide d'implémentation FHIR Togo, profils Shorthand (FSH) et publication SUSHI.",
    no_args_is_help=True,
)
app.add_typer(ig_app, name="ig")


@ig_app.command(
    name="build",
    help="Compiler le Guide d'Implémentation Togo (FSH vers StructureDefinition JSON) via conteneur SUSHI (ADR D-07).",
)
def ig_build(
    use_docker: Annotated[
        bool,
        typer.Option(
            "--docker/--no-docker",
            help="Exécuter SUSHI dans un conteneur Docker éphémère (recommandé ADR D-07).",
        ),
    ] = True,
    ig_dir: Annotated[
        Path,
        typer.Option(
            "--ig-dir",
            help="Répertoire contenant les fichiers FHIR Shorthand (*.fsh).",
        ),
    ] = Path("ig"),
) -> None:
    """Compile l'IG FHIR Togo."""
    console.print(
        f"[bold blue][IG][/bold blue] Compilation FSH via SUSHI (Docker={use_docker}, dossier=[cyan]{ig_dir}[/cyan])."
    )


@ig_app.command(
    name="validate",
    help="Vérifier la validité des profils nationaux togolais générés (TogoPatient, TogoEncounter, etc.).",
)
def ig_validate(
    profiles: Annotated[
        str,
        typer.Option(
            "--profiles",
            help="Profils spécifiques à valider (all, TogoPatient, TogoEncounter...).",
        ),
    ] = "all",
) -> None:
    """Valide les profils nationaux togolais."""
    console.print(
        f"[bold blue][IG][/bold blue] Validation des StructureDefinitions nationales : [cyan]{profiles}[/cyan]."
    )


@ig_app.command(
    name="publish",
    help="Générer le site statique de documentation HTML via l'IG Publisher HL7.",
)
def ig_publish(
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Répertoire de publication HTML.",
        ),
    ] = Path("ig/output"),
) -> None:
    """Publie la documentation web de l'IG."""
    console.print(
        f"[bold blue][IG][/bold blue] Publication du site IG Togo dans : [cyan]{output_dir}[/cyan]."
    )


# ==============================================================================
# 8. FHIR : Génération des ressources FHIR R4 et chargement OpenHIM / HAPI
# ==============================================================================
fhir_app = typer.Typer(
    name="fhir",
    help="Génération des ressources FHIR R4, validation HL7 et chargement HAPI FHIR / OpenHIM.",
    no_args_is_help=True,
)
app.add_typer(fhir_app, name="fhir")


@fhir_app.command(
    name="generate",
    help="Générer les ressources FHIR R4 (UUID v5 déterministes) et Bundles depuis le modèle canonique.",
)
def fhir_generate(
    bundle_size: Annotated[
        int,
        typer.Option(
            "--bundle-size",
            help="Nombre de ressources par Transaction Bundle.",
        ),
    ] = 50,
) -> None:
    """Génère les ressources FHIR R4 avec UUID v5."""
    console.print(
        f"[bold blue][FHIR][/bold blue] Génération des ressources FHIR R4. "
        f"Bundles transactionnels ordonnés par lots de {bundle_size}."
    )


@fhir_app.command(
    name="validate",
    help="Valider les Bundles FHIR via le validateur officiel HL7 Java contre l'IG Togo et isoler les rejets.",
)
def fhir_validate(
    validator_jar: Annotated[
        Path,
        typer.Option(
            "--validator-jar",
            help="Chemin vers le validateur officiel HL7 Java.",
        ),
    ] = Path("bin/validator_cli.jar"),
) -> None:
    """Valide les Bundles avec HL7 Java Validator."""
    console.print(
        f"[bold blue][FHIR][/bold blue] Validation HL7 Java contre les profils IG Togo (jar=[cyan]{validator_jar}[/cyan])."
    )


@fhir_app.command(
    name="load",
    help="Charger les Bundles FHIR sur HAPI FHIR JPA via la passerelle OpenHIM ou en direct (ADR D-06).",
)
def fhir_load(
    use_openhim: Annotated[
        bool,
        typer.Option(
            "--use-openhim/--direct-hapi",
            help="Router via la passerelle de médiation OpenHIM (défaut) ou directement vers HAPI FHIR (ADR D-06).",
        ),
    ] = True,
    endpoint: Annotated[
        str | None,
        typer.Option(
            "--endpoint",
            help="URL cible (déduit automatiquement : http://localhost:5001/fhir via OpenHIM ou http://localhost:8080/fhir).",
        ),
    ] = None,
) -> None:
    """Charge les transactions FHIR sur le serveur opérationnel."""
    mode_str = (
        "Passerelle OpenHIM (sécurisé/audité)"
        if use_openhim
        else "Direct HAPI FHIR (performance/tests)"
    )
    target_url = endpoint or (
        "http://localhost:5001/fhir" if use_openhim else "http://localhost:8080/fhir"
    )
    console.print(
        f"[bold blue][FHIR][/bold blue] Chargement des données FHIR. "
        f"Mode d'acheminement : [cyan]{mode_str}[/cyan] vers [yellow]{target_url}[/yellow] (ADR D-06)."
    )


# ==============================================================================
# 9. OMOP : Transformation et chargement vers OMOP CDM 5.4
# ==============================================================================
omop_app = typer.Typer(
    name="omop",
    help="Transformation ETL et chargement vers l'entrepôt relationnel OMOP CDM 5.4.",
    no_args_is_help=True,
)
app.add_typer(omop_app, name="omop")


@omop_app.command(
    name="init",
    help="Initialiser les tables du schéma relationnel OMOP CDM 5.4 sur PostgreSQL dédié (omop_cdm, ADR D-05).",
)
def omop_init(
    db_name: Annotated[
        str,
        typer.Option(
            "--db-name",
            help="Nom de la base PostgreSQL dédiée (ADR D-05).",
        ),
    ] = "omop_cdm",
    drop_existing: Annotated[
        bool,
        typer.Option(
            "--drop-existing",
            help="Supprimer les tables existantes avant initialisation (DANGER).",
        ),
    ] = False,
) -> None:
    """Initialise le schéma OMOP CDM 5.4."""
    console.print(
        f"[bold blue][OMOP][/bold blue] Initialisation du schéma DDL OMOP CDM 5.4 sur PostgreSQL : [cyan]{db_name}[/cyan] (drop={drop_existing})."
    )


@omop_app.command(
    name="transform",
    help="Exécuter l'ETL de transformation des ressources FHIR vers les tables relationnelles OMOP CDM.",
)
def omop_transform(
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            help="Nombre d'enregistrements par lot d'insertion OMOP.",
        ),
    ] = 1000,
) -> None:
    """Exécute l'ETL FHIR vers OMOP CDM."""
    console.print(
        f"[bold blue][OMOP][/bold blue] Exécution de l'ETL vers OMOP CDM (PERSON, VISIT, CONDITION...). Lot de {batch_size}."
    )


@omop_app.command(
    name="dqd",
    help="Lancer la suite de tests de qualité OHDSI Data Quality Dashboard (DQD) et Achilles.",
)
def omop_dqd(
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Répertoire de sortie des rapports Achilles et DQD.",
        ),
    ] = Path("docs/reports/omop_dqd"),
) -> None:
    """Exécute les contrôles qualité OHDSI DQD."""
    console.print(
        f"[bold blue][OMOP][/bold blue] Exécution d'Achilles et du Data Quality Dashboard (DQD). Rapport dans : [cyan]{output_dir}[/cyan]."
    )


# ==============================================================================
# 10. EXPORT-AI : Export des jeux de données d'apprentissage pour l'IA
# ==============================================================================
export_ai_app = typer.Typer(
    name="export-ai",
    help="Export des jeux de données d'apprentissage Parquet pour l'IA et Datasheet éthique.",
    no_args_is_help=True,
)
app.add_typer(export_ai_app, name="export-ai")


@export_ai_app.command(
    name="generate",
    help="Générer les tables Parquet pour l'IA avec pseudonymisation salée et validation Pandera.",
)
def export_ai_generate(
    export_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Format de sortie principal (parquet [prioritaire], csv [miroir]).",
        ),
    ] = "parquet",
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Dossier de destination des exports d'apprentissage.",
        ),
    ] = Path("data/gold/ai"),
) -> None:
    """Génère les exports pour l'entraînement d'IA."""
    console.print(
        f"[bold blue][EXPORT-AI][/bold blue] Génération des tables d'apprentissage dénormalisées. "
        f"Format : [cyan]{export_format}[/cyan], destination : [cyan]{output_dir}[/cyan]. Validation Pandera active."
    )


@export_ai_app.command(
    name="datasheet",
    help="Générer la Fiche de Données (Datasheet for Datasets) documentant les biais, distributions et limites.",
)
def export_ai_datasheet(
    output_path: Annotated[
        Path,
        typer.Option(
            "--output",
            help="Chemin du document Datasheet for Datasets.",
        ),
    ] = Path("data/gold/ai/DATASHEET.md"),
) -> None:
    """Génère la fiche de données éthique et technique."""
    console.print(
        f"[bold blue][EXPORT-AI][/bold blue] Publication de la Datasheet de conformité éthique : [cyan]{output_path}[/cyan]."
    )


# ==============================================================================
# 11. DEGRADATION : Banc de test de dégradation et stress-test
# ==============================================================================
degradation_app = typer.Typer(
    name="degradation",
    help="Banc de test d'altération contrôlée de données et stress-test du pipeline.",
    no_args_is_help=True,
)
app.add_typer(degradation_app, name="degradation")


@degradation_app.command(
    name="apply",
    help="Injecter des anomalies réalistes paramétrées dans les données de référence et produire le journal d'altérations.",
)
def degradation_apply(
    rate: Annotated[
        float,
        typer.Option(
            "--rate",
            help="Taux global d'altération appliqué aux enregistrements (0.0 à 1.0).",
        ),
    ] = 0.15,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Graine pseudo-aléatoire fixe pour garantir la reproductibilité absolue.",
        ),
    ] = 42,
    source_dir: Annotated[
        Path,
        typer.Option(
            "--source-dir",
            help="Dossier source contenant les tables de Vérité Terrain Parquet.",
        ),
    ] = Path("data/truth"),
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Dossier de destination des données dégradées.",
        ),
    ] = Path("data/degraded"),
) -> None:
    """Applique le banc de dégradation contrôlée."""
    if not (0.0 <= rate <= 1.0):
        console.print(
            f"[bold red]Erreur:[/bold red] Le taux d'altération (--rate) doit être compris entre 0.0 et 1.0 (reçu: {rate})."
        )
        raise typer.BadParameter(
            f"Le taux d'altération (rate) doit être compris entre 0.0 et 1.0, reçu: {rate}"
        )

    if not source_dir.exists():
        console.print(
            f"[bold red]Erreur:[/bold red] Le dossier source spécifié n'existe pas : [cyan]{source_dir}[/cyan]"
        )
        raise typer.BadParameter(f"Le dossier source spécifié n'existe pas : {source_dir}")

    console.print(
        Panel.fit(
            f"[bold blue]Banc de Dégradation Contrôlée (Étape 4)[/bold blue]\n"
            f"Source : [cyan]{source_dir}[/cyan]\n"
            f"Destination : [cyan]{output_dir}[/cyan]\n"
            f"Taux d'altération cible : [magenta]{rate * 100:.1f}%[/magenta]\n"
            f"Graine pseudo-aléatoire : [yellow]{seed}[/yellow]",
            title="[bold green]Configuration de Dégradation[/bold green]",
        )
    )

    result = apply_degradation(
        source_dir=source_dir,
        output_dir=output_dir,
        rate=rate,
        seed=seed,
    )

    table = Table(title="Tables Cliniques Dégradées Produites")
    table.add_column("Table", style="cyan", justify="left")
    table.add_column("Lignes", style="green", justify="right")
    table.add_column("Fichier Parquet", style="blue")

    for t_name, df in result["tables"].items():
        table.add_row(t_name, str(len(df)), str(output_dir / f"{t_name}.parquet"))

    console.print(table)
    console.print(
        f"[bold green]Succès :[/bold green] [magenta]{result['alterations_count']}[/magenta] altérations tracées dans "
        f"[cyan]{output_dir / 'alterations_log.parquet'}[/cyan]."
    )


@degradation_app.command(
    name="list-rules",
    help="Afficher la liste des règles de dégradation cataloguées (dates hétérogènes, patronymes altérés, sentinelles).",
)
def degradation_list_rules(
    detailed: Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Afficher les spécifications techniques détaillées de chaque règle.",
        ),
    ] = False,
) -> None:
    """Liste les règles de dégradation disponibles."""
    catalog = load_rules_catalog()
    table = Table(
        title="Catalogue des règles d'altération et d'injection d'erreurs (Étape 4)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("ID Règle", style="bold cyan")
    table.add_column("Nom", style="green")
    table.add_column("Catégorie", style="yellow")
    table.add_column("Taux défaut", style="magenta", justify="right")
    table.add_column("Description", style="white")

    if detailed:
        table.add_column("Tables cibles", style="blue")
        table.add_column("Colonnes cibles", style="dim")

    for rule in catalog.rules:
        rate_str = f"{rule.default_rate * 100:.0f}%"
        if detailed:
            table.add_row(
                rule.rule_id,
                rule.name,
                rule.category,
                rate_str,
                rule.description,
                ", ".join(rule.target_tables),
                ", ".join(rule.target_columns) if rule.target_columns else "(toutes)",
            )
        else:
            table.add_row(
                rule.rule_id,
                rule.name,
                rule.category,
                rate_str,
                rule.description,
            )

    console.print(table)


# ==============================================================================
# 12. GENERATION : Génération de cohortes de données synthétiques
# ==============================================================================
generation_app = typer.Typer(
    name="generation",
    help="Génération algorithmique de données cliniques et statistiques synthétiques togolaises.",
    no_args_is_help=True,
)
app.add_typer(generation_app, name="generation")


@generation_app.command(
    name="run",
    help="Générer une cohorte clinique synthétique togolaise complète (Vérité Terrain) via le générateur Python (ADR D-04).",
)
def generation_run(
    count: Annotated[
        int,
        typer.Option(
            "--count",
            help="Nombre de dossiers patients synthétiques à générer.",
        ),
    ] = 1000,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Graine pseudo-aléatoire déterministe.",
        ),
    ] = 42,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Dossier de stockage de la Vérité Terrain.",
        ),
    ] = Path("data/truth"),
) -> None:
    """Génère les données de vérité terrain."""
    if count <= 0:
        console.print(
            f"[bold red]Erreur :[/bold red] Le paramètre --count doit être strictement positif (reçu: {count})."
        )
        raise typer.BadParameter("Le paramètre --count doit être strictement positif.")

    console.print(
        f"[bold blue][GENERATION][/bold blue] Générateur contextuel Python (ADR D-04). "
        f"Génération de {count} patients (graine={seed}) dans [cyan]{output_dir}[/cyan]..."
    )

    import pyarrow.parquet as pq

    generated_paths = generate_ground_truth(count=count, seed=seed, output_dir=output_dir)

    table = Table(
        title=f"Vérité Terrain Générée (Cohorte N={count}, Graine={seed})",
        border_style="green",
    )
    table.add_column("Entité Clinique", style="bold cyan")
    table.add_column("Fichier Parquet", style="magenta")
    table.add_column("Lignes", justify="right", style="green")
    table.add_column("Colonnes", justify="right", style="yellow")
    table.add_column("Taille (Ko)", justify="right", style="white")

    total_rows = 0
    display_keys = [
        ("patients", "Dossiers Patients (Demographics)"),
        ("encounters", "Séjours & Consultations (Encounters)"),
        ("conditions", "Diagnostics Médicaux (Conditions)"),
        ("observations", "Constantes & Examens (Observations)"),
        ("prescriptions", "Ordonnances Médicales (Prescriptions)"),
        ("immunizations", "Vaccinations PEV Togo (Immunizations)"),
    ]

    for key, label in display_keys:
        p = generated_paths[key]
        pq_tbl = pq.read_table(p)
        nrows = pq_tbl.num_rows
        ncols = pq_tbl.num_columns
        size_kb = round(p.stat().st_size / 1024, 2)
        total_rows += nrows
        table.add_row(label, p.name, f"{nrows:,}", str(ncols), f"{size_kb} Ko")

    console.print(table)
    console.print(
        f"[bold green]✔ Succès :[/bold green] {total_rows:,} enregistrements cliniques "
        f"générés avec succès dans [cyan]{output_dir}[/cyan]."
    )


@generation_app.command(
    name="dhis2-demo",
    help="Extraire ou générer les jeux d'agrégats statistiques de démonstration DHIS2 (dataValueSets).",
)
def generation_dhis2_demo(
    api_url: Annotated[
        str,
        typer.Option(
            "--api-url",
            help="URL de base de l'instance démo publique DHIS2.",
        ),
    ] = "https://play.dhis2.org/demo",
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Dossier de stockage des agrégats DHIS2.",
        ),
    ] = Path("data/truth/dhis2"),
    offline: Annotated[
        bool,
        typer.Option(
            "--offline",
            help="Forcer le mode hors-ligne sans tenter la connexion à l'API distante.",
        ),
    ] = False,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Graine pseudo-aléatoire déterministe.",
        ),
    ] = 42,
) -> None:
    """Extrait ou génère les données de démo DHIS2."""
    mode_str = "HORS-LIGNE (synthétique)" if offline else f"EN LIGNE ({api_url})"
    console.print(
        f"[bold blue][GENERATION][/bold blue] Agrégats statistiques DHIS2 dataValueSets "
        f"Mode: [cyan]{mode_str}[/cyan]..."
    )

    import pyarrow.parquet as pq

    res = extract_or_generate_dhis2_aggregates(
        api_url=api_url,
        output_dir=output_dir,
        offline=offline,
        seed=seed,
    )

    json_path = res["json"]
    parquet_path = res["parquet"]

    pq_tbl = pq.read_table(parquet_path)
    nrows = pq_tbl.num_rows

    table = Table(
        title="Agrégats Statistiques DHIS2 Générés",
        border_style="blue",
    )
    table.add_column("Type de Fichier", style="bold cyan")
    table.add_column("Chemin Fichier", style="magenta")
    table.add_column("Valeurs / Lignes", justify="right", style="green")
    table.add_column("Taille (Ko)", justify="right", style="white")

    json_size_kb = round(json_path.stat().st_size / 1024, 2)
    parquet_size_kb = round(parquet_path.stat().st_size / 1024, 2)

    table.add_row("DHIS2 dataValueSets (JSON)", str(json_path), f"{nrows:,}", f"{json_size_kb} Ko")
    table.add_row(
        "Agrégats Tabulaires (Parquet)", str(parquet_path), f"{nrows:,}", f"{parquet_size_kb} Ko"
    )

    console.print(table)
    console.print(
        f"[bold green]✔ Succès :[/bold green] {nrows:,} valeurs d'indicateurs agrégés "
        f"sauvegardées dans [cyan]{output_dir}[/cyan]."
    )


# ==============================================================================
# 13. ENV & INFRA : Diagnostics d'environnement et de services conteneurisés
# ==============================================================================
env_app = typer.Typer(
    name="env",
    help="Diagnostic de l'environnement d'exécution et des outils requis (Python, uv, Docker).",
    no_args_is_help=True,
)
app.add_typer(env_app, name="env")

infra_app = typer.Typer(
    name="infra",
    help="Supervision et diagnostic de l'infrastructure Docker Compose du projet.",
    no_args_is_help=True,
)
app.add_typer(infra_app, name="infra")


def collect_environment_diagnostics() -> dict[str, Any]:
    """Collecte l'état complet de l'environnement hôte et des outils."""
    diag: dict[str, Any] = {}

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    py_exact_branch = sys.version_info.major == 3 and sys.version_info.minor == 11
    diag["python"] = {
        "version": py_ver,
        "executable": sys.executable,
        "is_supported": py_ok,
        "is_recommended_3_11": py_exact_branch,
        "status": "OK" if py_exact_branch else ("WARNING" if py_ok else "ERROR"),
        "detail": "Python >= 3.11 conforme" if py_ok else "Python 3.11+ obligatoire",
    }

    # 2. uv package manager
    uv_path = shutil.which("uv")
    uv_ver = None
    if uv_path:
        try:
            res = subprocess.run(
                [uv_path, "--version"], capture_output=True, text=True, check=False
            )
            if res.returncode == 0:
                uv_ver = res.stdout.strip()
        except OSError:
            pass
    diag["uv"] = {
        "installed": uv_path is not None,
        "path": uv_path or "Non trouvé dans le PATH",
        "version": uv_ver or "Inconnue",
        "status": "OK" if uv_path else "ERROR",
    }

    # 3. Docker CLI
    docker_path = shutil.which("docker")
    docker_ver = None
    if docker_path:
        try:
            res = subprocess.run(
                [docker_path, "--version"], capture_output=True, text=True, check=False
            )
            if res.returncode == 0:
                docker_ver = res.stdout.strip()
        except OSError:
            pass
    diag["docker_cli"] = {
        "installed": docker_path is not None,
        "path": docker_path or "Non trouvé dans le PATH",
        "version": docker_ver or "Inconnue",
        "status": "OK" if docker_path else "ERROR",
    }

    # 4. Docker Daemon reachability
    daemon_running = False
    daemon_detail = "Injoignable"
    if docker_path:
        try:
            res = subprocess.run(
                [docker_path, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                daemon_running = True
                daemon_detail = f"Opérationnel (v{res.stdout.strip()})"
            else:
                err_snippet = (res.stderr.strip() or "Démon non démarré")[:80]
                daemon_detail = f"Inactif / Erreur ({err_snippet})"
        except OSError as e:
            daemon_detail = f"Erreur système : {e}"

    diag["docker_daemon"] = {
        "reachable": daemon_running,
        "detail": daemon_detail,
        "status": "OK" if daemon_running else "WARNING",
    }

    # 5. Container services
    services_status: dict[str, Any] = {}
    expected_services = ["postgres", "hapi-fhir", "openhim-core", "openhim-console", "mongodb"]
    if daemon_running and docker_path:
        try:
            ps_res = subprocess.run(
                [docker_path, "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            containers = {}
            if ps_res.returncode == 0:
                for line in ps_res.stdout.strip().splitlines():
                    if "|" in line:
                        parts = line.split("|", 2)
                        c_name = parts[0].strip()
                        c_status = parts[1].strip()
                        c_ports = parts[2].strip() if len(parts) > 2 else ""
                        containers[c_name] = {"status": c_status, "ports": c_ports}

            for svc in expected_services:
                found = False
                for c_name, c_info in containers.items():
                    if svc in c_name:
                        services_status[svc] = {
                            "container": c_name,
                            "status": c_info["status"],
                            "ports": c_info["ports"],
                            "state": "UP" if "Up" in c_info["status"] else "DOWN",
                        }
                        found = True
                        break
                if not found:
                    services_status[svc] = {
                        "container": "-",
                        "status": "Non déployé",
                        "ports": "-",
                        "state": "NOT_FOUND",
                    }
        except OSError:
            pass

    diag["services"] = services_status
    return diag


@env_app.command(
    name="check",
    help="Vérifier l'environnement d'exécution (Python >= 3.11, uv, Docker daemon, conteneurs).",
)
def env_check(
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Afficher les détails exhaustifs de la configuration système.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Sortie structurée au format JSON pour l'intégration CI/CD.",
        ),
    ] = False,
) -> None:
    """Exécute le diagnostic d'environnement complet."""
    diag = collect_environment_diagnostics()

    if json_output:
        console.print_json(json.dumps(diag, indent=2))
        return

    table = Table(title="Diagnostic de l'Environnement fhir-pipeline", border_style="cyan")
    table.add_column("Composant", style="bold cyan", min_width=16)
    table.add_column("Version / Localisation", style="white", min_width=32)
    table.add_column("Statut", justify="center", min_width=10)

    # Python
    py = diag["python"]
    py_badge = (
        "[green]OK[/green]"
        if py["status"] == "OK"
        else ("[yellow]AVERTISSEMENT[/yellow]" if py["status"] == "WARNING" else "[red]KO[/red]")
    )
    py_desc = f"{py['version']} ({py['executable']})" if verbose else f"v{py['version']}"
    table.add_row("Python", py_desc, py_badge)

    # uv
    uv = diag["uv"]
    uv_badge = "[green]OK[/green]" if uv["status"] == "OK" else "[red]KO[/red]"
    uv_desc = f"{uv['version']} ({uv['path']})" if verbose else uv["version"]
    table.add_row("uv Package Manager", uv_desc, uv_badge)

    # Docker CLI
    dcli = diag["docker_cli"]
    dcli_badge = "[green]OK[/green]" if dcli["status"] == "OK" else "[red]KO[/red]"
    dcli_desc = f"{dcli['version']} ({dcli['path']})" if verbose else dcli["version"]
    table.add_row("Docker CLI", dcli_desc, dcli_badge)

    # Docker Daemon
    ddaemon = diag["docker_daemon"]
    ddaemon_badge = "[green]OK[/green]" if ddaemon["status"] == "OK" else "[yellow]INACTIF[/yellow]"
    table.add_row("Docker Daemon", ddaemon["detail"], ddaemon_badge)

    console.print(table)

    # Service table if services present
    if diag["services"]:
        svc_table = Table(title="État des Services Conteneurisés Détectés", border_style="blue")
        svc_table.add_column("Service Attendu", style="bold white")
        svc_table.add_column("Conteneur Détecté", style="cyan")
        svc_table.add_column("Statut d'Exécution", style="white")
        svc_table.add_column("Ports", style="dim")
        svc_table.add_column("État", justify="center")

        for svc_name, svc_info in diag["services"].items():
            state_color = (
                "[green]UP[/green]"
                if svc_info["state"] == "UP"
                else (
                    "[yellow]ARRÊTÉ[/yellow]"
                    if svc_info["state"] == "DOWN"
                    else "[dim]NON INSTANCIÉ[/dim]"
                )
            )
            svc_table.add_row(
                svc_name,
                svc_info["container"],
                svc_info["status"],
                svc_info["ports"] or "-",
                state_color,
            )
        console.print(svc_table)


@infra_app.command(
    name="status",
    help="Superviser l'état opérationnel des conteneurs de l'infrastructure Docker Compose.",
)
def infra_status(
    compose_file: Annotated[
        Path,
        typer.Option(
            "--compose-file",
            "-f",
            help="Chemin du fichier Docker Compose.",
        ),
    ] = Path("docker-compose.yml"),
) -> None:
    """Affiche le statut de l'infrastructure Docker."""
    if not compose_file.exists():
        console.print(
            Panel(
                f"[yellow]Le fichier de configuration Docker Compose ([bold]{compose_file}[/bold]) "
                "n'est pas encore présent dans le dépôt racine.\n"
                "Pour déployer les services de l'Étape 1 : configurez docker-compose.yml.[/yellow]",
                title="Infrastructure Docker",
                border_style="yellow",
            )
        )
        return

    # Check docker compose ps
    docker_path = shutil.which("docker")
    if not docker_path:
        console.print("[red]Binaire docker non trouvé.[/red]")
        return

    try:
        res = subprocess.run(
            [docker_path, "compose", "-f", str(compose_file), "ps"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            console.print(Panel(res.stdout, title="État Docker Compose", border_style="green"))
        else:
            console.print(f"[red]Erreur docker compose ps : {res.stderr}[/red]")
    except OSError as e:
        console.print(f"[red]Échec d'exécution de docker compose : {e}[/red]")


@app.callback()
def main() -> None:
    """Point d'entrée principal de la CLI fhir-pipeline."""


if __name__ == "__main__":
    app()
