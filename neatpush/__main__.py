import typer

from .neatmanga import NeatMangaClient

cli = typer.Typer()


neatmanga = NeatMangaClient()


@cli.command("fetch")
def fetch(manga: str = "berserk"):
    results = neatmanga.get_latest_releases(manga)
    print(results)


@cli.command("ping")
def ping():
    print("ping")


if __name__ == "__main__":
    cli()
