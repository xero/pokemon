#!/usr/bin/env python3
"""Fill in the quantity column of product-ids.tsv.

    python3 scrape_quantities.py [--dry-run]

How many of a card we own comes from two places, so this merges rather than
overwrites. Overwriting from order history alone would zero out the 18 Fire
Energy that came in Fox's theme deck.

    quantity = singles ordered + copies inside sealed products owned

order-quantities.tsv is the singles half, scraped out of the browser because
the page needs a logged-in session. Regenerate it by opening

    https://store.tcgplayer.com/myaccount/orderhistory

and running this in the console, then saving the output:

    const all = [];
    for (const n of [1, 2, 3]) {
      const html = n === 1 ? document.documentElement.outerHTML
        : await (await fetch('/myaccount/orderhistory?PageNumber=' + n,
                             {credentials: 'same-origin'})).text();
      const d = new DOMParser().parseFromString(html, 'text/html');
      for (const c of d.querySelectorAll('td.orderHistoryQuantity')) {
        const tr = c.closest('tr'), a = tr.querySelector('a[href^="/"]');
        all.push([a.getAttribute('href').replace(/\\/listing\\?.*$/, ''),
                  parseInt(c.textContent.trim(), 10)]);
      }
    }
    const sum = {};
    for (const [h, q] of all) sum[h] = (sum[h] || 0) + q;
    Object.entries(sum).sort().map(([h, q]) => h + '\\t' + q).join('\\n')

Set the date filter to the year rather than "Last 30 Days" or older orders are
silently dropped. Check every year with orders in it; the pager is ?PageNumber=N.

A row the merge knows nothing about keeps whatever quantity it already has, so
wishlist rows sitting at 0 survive a re-run untouched.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "product-ids.tsv"
ORDERS = ROOT / "order-quantities.tsv"
SEALED = ROOT / "sealed-contents.tsv"

# Order history lists these next to the cards. They are not cards.
NOT_A_CARD = re.compile(r"^/(storage-albums|supplies|accessories)/")


def path_of(url):
    return re.sub(r"^https?://store\.tcgplayer\.com", "", url.strip())


def read_orders():
    """{card path: copies bought as singles}, minus sealed boxes and supplies."""
    out, sealed_boxes = {}, []
    if not ORDERS.exists():
        print(f"  no {ORDERS.name}; sealed products only", file=sys.stderr)
        return out, sealed_boxes
    for line in ORDERS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        path, qty = line.rsplit("\t", 1)
        path = path.strip()
        if NOT_A_CARD.match(path):
            continue
        out[path] = out.get(path, 0) + int(qty)
    return out, sealed_boxes


def read_sealed():
    """{card path: copies}, expanded from the decks in sealed-contents.tsv."""
    out, unlinked = {}, []
    for line in SEALED.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("product\t"):
            continue
        product, _sealed, qty, url, card = (line.split("\t") + [""] * 5)[:5]
        if not url.strip():
            unlinked.append((product, card.strip()))
            continue
        out[url.strip()] = out.get(url.strip(), 0) + int(qty)
    return out, unlinked


def main():
    dry = "--dry-run" in sys.argv
    orders, _ = read_orders()
    sealed, unlinked = read_sealed()

    # a sealed box is bought as one line item; its cards are counted from the
    # decklist instead, so the box itself must not become a card. match on the
    # product slug only: the MBG *set* slug also contains "starter-set", so
    # matching the whole path would delete every card in it.
    boxes = {p for p in orders
             if re.search(r"(starter-set|theme-deck|booster-box|elite-trainer)",
                          p.rsplit("/", 1)[-1])}
    for p in boxes:
        del orders[p]

    rows, changed, unseen = [], [], set(orders) | set(sealed)
    for line in SEED.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        pid, url = parts[0], parts[1]
        was = parts[2] if len(parts) > 2 else ""
        path = path_of(url)
        unseen.discard(path)
        if path in orders or path in sealed:
            now = str(orders.get(path, 0) + sealed.get(path, 0))
        else:
            now = was or "0"          # wishlist rows and anything hand-set
        if now != was:
            changed.append((path, was or "-", now))
        rows.append(f"{pid}\t{url}\t{now}")

    print(f"  {len(rows)} seed rows, {len(changed)} quantities changed")
    for path, a, b in changed[:8]:
        print(f"    {a:>3} -> {b:<3} {path}")
    if len(changed) > 8:
        print(f"    ... and {len(changed) - 8} more")
    if unseen:
        print(f"  {len(unseen)} cards owned but not in the seed:", file=sys.stderr)
        for p in sorted(unseen):
            print(f"    {p}", file=sys.stderr)
    if unlinked:
        print(f"  {len(unlinked)} sealed cards have no seed row yet:", file=sys.stderr)
        for product, card in unlinked[:6]:
            print(f"    {product}: {card}", file=sys.stderr)
        if len(unlinked) > 6:
            print(f"    ... and {len(unlinked) - 6} more", file=sys.stderr)

    total = sum(int(r.split("\t")[2]) for r in rows)
    print(f"  {total} cards owned across {sum(1 for r in rows if r.split(chr(9))[2] != '0')} rows")
    if dry:
        print("  --dry-run, nothing written")
        return
    SEED.write_text("\n".join(rows) + "\n", encoding="utf-8")


main()
