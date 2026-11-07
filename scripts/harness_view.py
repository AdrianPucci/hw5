"""Make an easy-to-read copy of output/harness.md: Calibri, bold headers, indented sections.

Writes output/harness_view.html (open it in any browser). The .md file stays the one you edit;
run this again after editing to refresh the view.

Run from the HMW 5 folder:  python scripts/harness_view.py
"""

import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "output"
SOURCE = OUTPUT / "harness.md"
TARGET = OUTPUT / "harness_view.html"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Customs Harness</title>
<style>
  :root { --bg:#ffffff; --ink:#1b2430; --muted:#5d6b7c; --line:#d9e0ea; --blue:#00356b; --head:#e8eef6;
          --note:#fff6d6; --noteline:#e0a800; --code:#f1f4f8; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#11161d; --ink:#e6ebf1; --muted:#98a5b5; --line:#2d3744; --blue:#8db8ea; --head:#222c38;
            --note:#3a3216; --noteline:#c99a12; --code:#1f2733; }
  }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:12pt/1.5 Calibri, Carlito, "Segoe UI", sans-serif; padding:24px 16px; }
  main { max-width:960px; margin:auto; }
  h1, h2, h3, h4 { font-weight:700; color:var(--blue); line-height:1.25; overflow-wrap:anywhere; }
  h1 { font-size:24pt; margin:0 0 12px; }
  h2 { font-size:17pt; margin:32px 0 10px; padding-bottom:4px; border-bottom:2px solid var(--line); }
  h3 { font-size:13.5pt; margin:22px 0 8px 2em; }
  hr { border:0; border-top:1px solid var(--line); margin:24px 0; }
  ul, ol { padding-left:1.6em; } li { margin:3px 0; } li > ul, li > ol { margin-top:3px; }
  table { border-collapse:collapse; display:block; overflow-x:auto; max-width:100%; }
  th, td { border:1px solid var(--line); padding:5px 9px; text-align:left; vertical-align:top; }
  th { background:var(--head); font-weight:700; }
  code { font-family:Consolas, monospace; font-size:0.9em; background:var(--code); padding:1px 4px; border-radius:3px; }
  blockquote { border-left:4px solid var(--line); color:var(--muted); padding:2px 12px; }
  .adrian { background:var(--note); border-left:4px solid var(--noteline); padding:6px 10px; border-radius:4px; }
  .stamp { color:var(--muted); font-size:10pt; }
</style></head>
<body><main id="doc"></main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script>
  const md = __MD__;
  const doc = document.getElementById("doc");
  doc.innerHTML = window.marked ? marked.parse(md) : "<pre>" + md.replace(/</g, "&lt;") + "</pre>";
  // Highlight Adrian's own answers so they're easy to find.
  doc.querySelectorAll("p, li").forEach(el => { if (el.textContent.includes("\\u{1F6D1}")) el.classList.add("adrian"); });
  // Indent everything under a header one step further than the header (h3 sits under h2).
  let inH3 = false;
  for (const el of [...doc.children]) {
    if (el.tagName === "H2" || el.tagName === "H1") inH3 = false;
    else if (el.tagName === "H3") inH3 = true;
    else if (el.tagName !== "HR") el.style.marginLeft = inH3 ? "4em" : "2em";
  }
</script>
</body></html>
"""


def read_markdown(path: Path) -> str:
    """Read harness.md whether Word/Notepad saved it as UTF-8 or UTF-16."""
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


if __name__ == "__main__":
    text = read_markdown(SOURCE)
    TARGET.write_text(PAGE.replace("__MD__", json.dumps(text)), encoding="utf-8")
    print(f"Wrote {TARGET.name} from {SOURCE.name}")
