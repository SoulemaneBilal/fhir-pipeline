"""Interface en ligne de commande (CLI) du pipeline FHIR Togo."""

import typer

app = typer.Typer(
    name="fhir-pipeline",
    help="Pipeline de standardisation et d'interopérabilité de données de santé (Togo).",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Point d'entrée principal de la CLI fhir-pipeline."""


if __name__ == "__main__":
    app()
