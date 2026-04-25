from pathlib import Path
import shutil
import sys


def guard_runs_root(runs_root: Path, force: bool, resume: bool):

    runs_root = Path(runs_root)

    if not runs_root.exists():
        # Fresh run
        runs_root.mkdir(parents=True)
        return

    # Directory exists
    is_empty = not any(runs_root.iterdir())

    if is_empty:
        return  # Safe

    if resume:
        return  # Restart logic will handle skipping

    if force:
        print(f"Overwriting existing run directory: {runs_root}")
        shutil.rmtree(runs_root)
        runs_root.mkdir(parents=True)
        return

    print(
        f"\nERROR: Run directory '{runs_root}' already exists and is not empty.\n"
        "Use --resume to continue or --force to overwrite.\n"
    )
    sys.exit(1)