# deed-page

The official [deed.page](https://deed.page) CLI and Python client. Publish a file or a folder to a permanent `https://{slug}.deed.page/` URL. You don't need an account, an email address or a claim link, and nothing expires after 24 hours.

## Quickstart

```bash
pip install deed-page            # or: pipx install deed-page / uvx deed-page
deed-page publish ./site --slug my-launch-7f3k
# https://my-launch-7f3k.deed.page/  (version v1)
# New owner token saved to ~/.config/deed-page/token
```

To update the site, run the same command again. Every publish is saved as a new version:

```bash
deed-page update ./site --slug my-launch-7f3k
deed-page list
deed-page delete my-launch-7f3k
```

It needs Python 3.8 or later and uses only the standard library. `python -m deed_page` works too.

## Token

The first publish without a token creates an owner token. The CLI saves it to `~/.config/deed-page/token` (directory mode 700, file mode 600) and never prints it. Later commands read the token from:

1. `DEED_PAGE_TOKEN` (or `DEEDPAGE_TOKEN`)
2. `~/.config/deed-page/token` (`$XDG_CONFIG_HOME/deed-page/token` if that is set)

The token is the only key that can update or delete your sites. deed.page stores only its SHA-256 hash. To manage billing or attach an optional recovery email, open https://deed.page/account.

## Commands

| Command | What it does |
| --- | --- |
| `publish <path> --slug <slug>` | Publishes a file or folder. A single `.html` file becomes `index.html`. |
| `update <path> --slug <slug>` | Same as `publish`, but fails if no token is found. |
| `list` | Lists the sites you own. |
| `delete <slug>` | Deletes a site you own. |
| `whoami` | Shows your plan and usage. |

Options: `--merge` replaces only the paths you send, `--spa` turns on single-page-app routing, `--ttl <seconds>` makes the site expire, and `--json` prints the raw response with tokens redacted.

## Library

```python
from deed_page import DeedPage

dp = DeedPage()  # reads DEED_PAGE_TOKEN or ~/.config/deed-page/token
site = dp.publish("./dist", slug="my-launch-7f3k")
print(site["url"])

# Files held in memory work too:
dp.publish({"index.html": "<!doctype html><h1>Hi</h1>"}, slug="my-launch-7f3k")
dp.delete("my-launch-7f3k")
```

## Limits

The Free plan gives you 25 sites, 25 MB per site and 60 publishes an hour. Free sites show a small "Published with deed.page" badge. Each request is capped at 4 MB, and this CLI refuses larger uploads before sending them. For bigger sites, use the manifest upload in the [docs](https://deed.page/docs). Plans and prices are at https://deed.page/pricing.

## License

MIT © Avatar 8 LLC. Support: ops@avatar33.com
