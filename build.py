#!/usr/bin/env python3
"""Build every generated file, in the order they depend on each other.

    python3 build.py            # the site
    python3 build.py --check    # build, then fail if the result differs from git
    python3 build.py --data     # re-fetch cards.csv first, then build

The order matters and is not obvious, which is the reason this file exists.
build_index.py reads the finished pages back to count the cards on each one, so
it has to run after every page it links to. Running the builders by hand in the
wrong order produced an index claiming one card for an eight-card page, twice.

--check is the regression test. Every generated file is committed, so a clean
tree after a build proves the committed HTML still matches the sources it came
from. CI runs it; run it yourself before committing a change to a builder.
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent

# (what it makes, what to run). Order is the dependency order, not preference.
STEPS = [
    ("collection.html", "build_html.py"),
    ("the deck pages", "build_deck_html.py"),
    ("credits.html", "build_credits.py"),
    ("collection.md", "build_markdown.py"),
    # last, and it has to be: this one reads the pages above back off disk
    ("index.html", "build_index.py"),
]

# Not part of a build. It goes to the network, downloads card scans, and
# rewrites cards.csv, so it runs only when asked for.
DATA = "normalize_cards.py"


def run(script):
    r = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"\n{script} failed, stopping here")


def main():
    if "--data" in sys.argv:
        print(f"== {DATA}")
        run(DATA)
    for label, script in STEPS:
        print(f"== {label}")
        run(script)

    if "--check" not in sys.argv:
        return
    # --porcelain lists nothing when the tree is clean, whatever the file
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not dirty:
        print("\ncheck: the committed build matches its sources")
        return
    print("\ncheck: a build changed these files, so the commit is stale:\n")
    print(dirty)
    subprocess.run(["git", "--no-pager", "diff", "--stat"], cwd=ROOT)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
