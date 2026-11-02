"""claimreg command line: `python3 -m claimreg <command>`."""
import argparse
import sys

import yaml
from pathlib import Path

from . import registry
from .applies import CONTEXT_SIZES, applicable
from .config_check import (check_citation, compare_lock, lock_text, parse_citations,
                           registry_date)
from .quotes import check_quotes
from .snapshots import SOURCES_DIR, save_snapshot, snapshot_diff
from .validate import stale_claims, validate


def _rel(path, root):
    try:
        return Path(path).relative_to(root)
    except ValueError:
        return path


def cmd_validate(args):
    reg = registry.load(args.root)
    errors = validate(reg)
    for path, msg in errors:
        print(f"{_rel(path, reg.root)}: {msg}")
    stale = stale_claims(reg)
    for claim in stale:
        print(f"{_rel(claim.path, reg.root)}: stale since {claim.data['review_by']}")
    print(f"{len(reg.claims)} claims, {len(errors)} errors, {len(stale)} stale")
    return 1 if errors else 0


def cmd_check_quotes(args):
    reg = registry.load(args.root)
    pages, diffed, bad = {}, set(), 0
    for claim, n, url, status in check_quotes(reg, ids=set(args.ids) or None, pages=pages):
        if status != "ok":
            bad += 1
        if status != "ok" or args.verbose:
            print(f"{status.upper() if status in ('ok', 'missing') else status}  "
                  f"{claim.id} evidence[{n}]  {url}")
        if status == "missing":
            _print_diff(reg.root, url, pages[url], diffed)
    if args.save_sources:
        written = [url for url, page in pages.items()
                   if not isinstance(page, Exception) and save_snapshot(reg.root, url, page)]
        print(f"{len(written)} source snapshots written")
    print(f"{bad} quotes not found")
    return 1 if bad else 0


def _print_diff(root, url, page, diffed):
    """Show how the page changed since its snapshot, once per URL."""
    if url in diffed:
        print("    (page diff shown above)")
        return
    diffed.add(url)
    diff = snapshot_diff(root, url, page)
    if diff is None:
        print(f"    no snapshot of this page in {SOURCES_DIR}/; nothing to compare against")
    elif not diff:
        print("    page text unchanged since its snapshot")
    else:
        for line in diff:
            print("    " + line)


def cmd_applies(args):
    reg = registry.load(args.root)
    try:
        rows = applicable(reg, args.model, args.version, args.context_size)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    width = max((len(c.id) for c, _ in rows), default=0)
    for claim, conds in rows:
        direction = (claim.data.get("effect") or {}).get("direction")
        line = f"{claim.id:<{width}}  {direction:<9}  {' '.join(conds)}"
        print(line.rstrip())
    size = f", {args.context_size} context" if args.context_size else ""
    print(f"{len(rows)} claims apply to {args.model} {args.version}{size}")
    return 0


def cmd_check_config(args):
    reg = registry.load(args.root)
    config = Path(args.config)
    lock_path = Path(args.lock) if args.lock else config.parent / "claims.lock"
    citations = parse_citations(config.read_text())
    problems = warnings = 0
    for line, cid, major in citations:
        findings, details, problem = check_citation(reg, cid, major)
        problems += problem
        warnings += any(f.startswith("stale") for f in findings)
        if findings != ["ok"] or args.verbose:
            print(f"{config}:{line}: {cid}@{major}  {'; '.join(findings)}")
            for d in details:
                print("    " + d)
    cited = [cid for _, cid, _ in citations]
    if args.write_lock:
        versions = {cid: reg.claims[cid].data.get("version") for cid in cited if cid in reg.claims}
        date, tagged = registry_date(reg.root)
        lock_path.write_text(lock_text(date, versions, tagged))
        note = "" if tagged else " (registry untagged: dated today)"
        print(f"wrote {lock_path} with {len(versions)} claims{note}")
    elif lock_path.exists():
        for msg, details, problem in compare_lock(reg, yaml.safe_load(lock_path.read_text()), cited):
            problems += problem
            print(msg)
            for d in details:
                print("    " + d)
    print(f"{len(citations)} citations, {problems} problems, {warnings} stale")
    return 1 if problems else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="claimreg", description="Claim registry tools.")
    p.add_argument("--root", default=".", help="registry checkout (default: current directory)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check every claim against docs/claim-format.md") \
        .set_defaults(func=cmd_validate)
    q = sub.add_parser("check-quotes", help="fetch each source and confirm its quote is on the page")
    q.add_argument("ids", nargs="*", help="only these claim ids (default: all)")
    q.add_argument("-v", "--verbose", action="store_true", help="also list quotes that were found")
    q.add_argument("--save-sources", action="store_true",
                   help=f"write the plain-text snapshot of each fetched page to {SOURCES_DIR}/")
    q.set_defaults(func=cmd_check_quotes)
    a = sub.add_parser("applies", help="list the active claims that apply to a model and version")
    a.add_argument("--model", required=True, help="family or line, e.g. claude-sonnet")
    a.add_argument("--version", required=True, help="a version listed for it, e.g. 5.5")
    a.add_argument("--context-size", choices=CONTEXT_SIZES,
                   help="drop claims for the other input size (default: keep all, show the condition)")
    a.set_defaults(func=cmd_applies)
    k = sub.add_parser("check-config", help="check the claims a config cites, and its claims.lock")
    k.add_argument("config", help="config file citing claims as <!-- claim: id@major -->")
    k.add_argument("--lock", help="lock file (default: claims.lock next to the config)")
    k.add_argument("--write-lock", action="store_true",
                   help="write the lock with every cited claim at its current version")
    k.add_argument("-v", "--verbose", action="store_true", help="also list citations that are ok")
    k.set_defaults(func=cmd_check_config)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
