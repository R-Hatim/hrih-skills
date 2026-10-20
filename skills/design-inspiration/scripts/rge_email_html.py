"""Fetch the raw HTML of an email from reallygoodemails.com.

Usage:
    python rge_email_html.py <slug-or-url> [output.html]

    python rge_email_html.py dropbox-app-file-editing
    python rge_email_html.py https://reallygoodemails.com/emails/dropbox-app-file-editing ref.html

Prints the HTML (or writes it to output.html), followed by the email's
screenshot URLs on stderr. Study the markup for structure (table layout,
widths, mobile media queries, dark-mode handling). Don't ship another brand's
email as your own.
"""
import re
import sys
import urllib.request


def slug_from(arg: str) -> str:
    m = re.search(r"/emails/([^/?#]+)", arg)
    return m.group(1) if m else arg.strip("/")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    slug = slug_from(sys.argv[1])
    # The RSC header makes Next.js return the page's data payload, which embeds the email HTML.
    req = urllib.request.Request(
        f"https://reallygoodemails.com/emails/{slug}",
        headers={"RSC": "1", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8", "replace")

    m = re.search(r":T[0-9a-f]+,(<!DOCTYPE.*?</html>)", payload, re.S | re.I)
    if not m:
        print(f"No email HTML found for '{slug}'. Open https://reallygoodemails.com/emails/{slug}/code in a browser instead.", file=sys.stderr)
        return 1

    html = m.group(1)
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Wrote {len(html):,} chars to {sys.argv[2]}", file=sys.stderr)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(html)

    base = "https://pro-really-good-emails.s3.eu-west-1.amazonaws.com/emails"
    print(f"Desktop screenshot: {base}/{slug}.png\nMobile screenshot:  {base}/mobile/{slug}.png", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
