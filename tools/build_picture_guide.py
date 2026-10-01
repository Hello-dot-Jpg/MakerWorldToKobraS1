"""Make an offline picture guide from the root Markdown and local SVG drawings.

No browser, desktop capture, network or third-party dependencies are needed.
The output HTML is self-contained and can be opened by double-clicking it.
"""
import argparse
import html
from pathlib import Path
import re


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)


def render(repo):
    source = (repo / "USING_THE_APP.md").read_text(encoding="utf-8")
    body = []
    for block in re.split(r"\n\s*\n", source.strip()):
        picture = re.fullmatch(r"!\[([^\]]+)\]\((docs/images/[^)]+\.svg)\)", block)
        if picture:
            path = (repo / picture[2]).resolve()
            if path.parent != (repo / "docs" / "images").resolve():
                raise ValueError("Picture path outside guide image folder")
            svg = path.read_text(encoding="utf-8")
            prefix = path.stem
            svg = svg.replace('id="title"', f'id="{prefix}-title"')
            svg = svg.replace('id="desc"', f'id="{prefix}-desc"')
            svg = svg.replace('aria-labelledby="title desc"',
                f'aria-labelledby="{prefix}-title {prefix}-desc"')
            body.append('<figure>' + svg + '</figure>')
        elif block.startswith("## "):
            body.append("<h2>" + inline(block[3:]) + "</h2>")
        elif block.startswith("# "):
            body.append("<h1>" + inline(block[2:]) + "</h1>")
        else:
            block = block.replace("(docs/EXTRA_OPTIONS.md)",
                "(https://github.com/Hello-dot-Jpg/MakerWorldToKobraS1/blob/main/docs/EXTRA_OPTIONS.md)")
            body.append("<p>" + inline(block.replace("\n", " ")) + "</p>")
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kobra S1 — Start here</title>
<style>
body { background:#f5f7fa; color:#19202b; font:20px/1.55 system-ui, sans-serif;
       max-width:1040px; margin:32px auto; padding:0 18px 48px; }
h1 { font-size:34px; line-height:1.2; } h2 { font-size:29px; margin-top:44px; }
figure { margin:20px 0 30px; } svg { display:block; width:100%; height:auto; }
a { color:#005eb8; } strong { font-weight:750; }
code { font-size:0.92em; overflow-wrap:anywhere; }
@media print { body { background:white; font-size:15px; } h2 { break-after:avoid; }
figure { break-inside:avoid; } }
</style></head><body>''' + "\n".join(body) + '</body></html>\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New output HTML path (never overwritten)")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    with args.output.open("x", encoding="utf-8") as output:
        output.write(render(repo))
    print(args.output.resolve())


if __name__ == "__main__":
    main()
