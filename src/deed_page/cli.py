"""deed-page command line interface."""
import argparse
import json
import sys

from . import __version__
from .client import DeedPage, DeedPageError, redact, token_path, TOKEN_RE


def _parser():
    p = argparse.ArgumentParser(
        prog="deed-page",
        description="Publish files to a permanent https://{slug}.deed.page/ URL.",
        epilog="Token: DEED_PAGE_TOKEN (or DEEDPAGE_TOKEN), else %s. The first publish without a token "
               "creates one and saves it there (mode 600). The token is never printed. Docs: https://deed.page/docs"
               % token_path(),
    )
    p.add_argument("-v", "--version", action="version", version=__version__)
    p.add_argument("--json", action="store_true", help="print the raw JSON response (tokens redacted)")
    p.add_argument("--client", help="X-Client name sent to deed.page (default deed-page-pypi/%s)" % __version__)
    sub = p.add_subparsers(dest="cmd")
    for name, helptext in (("publish", "publish a file or folder"), ("update", "update a site you own")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("path")
        s.add_argument("--slug", required=True)
        s.add_argument("--merge", action="store_true", help="replace only the paths you send")
        s.add_argument("--spa", action="store_true", help="single-page-app routing")
        s.add_argument("--ttl", type=int, help="expire the site after this many seconds")
    sub.add_parser("list", help="list the sites you own")
    d = sub.add_parser("delete", help="delete a site you own")
    d.add_argument("slug")
    sub.add_parser("whoami", help="show your plan and usage")
    return p


def main(argv=None):
    parser = _parser()
    # allow --json / --client after the subcommand too
    argv = list(sys.argv[1:] if argv is None else argv)
    pre = [a for a in argv if a == "--json"]
    argv = pre + [a for a in argv if a != "--json"]
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    dp = DeedPage(client=args.client)

    def out(data, line):
        print(json.dumps(redact(data), indent=2) if args.json else line)

    try:
        if args.cmd in ("publish", "update"):
            fn = dp.update if args.cmd == "update" else dp.publish
            r = fn(args.path, args.slug, merge=args.merge, spa=args.spa, ttl=args.ttl)
            line = "%s  (version %s)" % (r.get("url"), r.get("version"))
            if r.get("token_saved_to"):
                line += ("\nNew owner token saved to %s. Keep it private: it is the only key to update or "
                         "delete this site." % r["token_saved_to"])
                badge = r.get("badge") or {}
                if badge.get("shown"):
                    line += ('\nFree sites show a small "Published with deed.page" badge. Remove it: %s'
                             % (badge.get("upgrade_url") or "https://deed.page/pricing"))
            out(r, line)
        elif args.cmd == "list":
            r = dp.list()
            sites = r.get("sites") or []
            if args.json:
                out(r, "")
            elif not sites:
                print("No sites.")
            else:
                for s in sites:
                    print("%s\t%s\t%s" % (s.get("slug"), s.get("url") or "https://%s.deed.page/" % s.get("slug"),
                                          s.get("version", "")))
        elif args.cmd == "delete":
            out(dp.delete(args.slug), "Deleted %s" % args.slug)
        elif args.cmd == "whoami":
            r = dp.whoami()
            plan = r.get("plan")
            plan = (plan.get("name") or plan.get("id")) if isinstance(plan, dict) else (plan or r.get("stripe_plan"))
            out(r, "plan: %s  sites: %s/%s  domains: %s/%s" % (plan, r.get("sites", "?"), r.get("site_limit", "?"),
                                                               r.get("domains", "?"), r.get("domain_limit", "?")))
    except (DeedPageError, OSError, ValueError) as e:
        msg = TOKEN_RE.sub("<redacted>", str(e))
        if isinstance(e, DeedPageError) and e.status:
            msg += " (HTTP %s%s)" % (e.status, " " + e.code if e.code else "")
        print("deed-page: %s" % msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
