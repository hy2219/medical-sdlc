#!/usr/bin/env python3
"""Build site/index.html from the repository's paper and analysis records.

The dashboard is a single self-contained file: no fetch, no modules, no network.
Double-clicking it on a hospital laptop has to work, so the data is inlined.
"""

import base64
import json
import mimetypes
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "site" / "dashboard.template.html"
OUTPUT = ROOT / "site" / "index.html"


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"skipping {path}: {error}", file=sys.stderr)
        return None


def inline_figure(analysis, directory):
    """Turn a figure file next to analysis.json into markup the page can hold."""
    figure = analysis.get("figure") or ""
    if figure.strip().startswith("<"):
        return
    for path in ([directory / figure] if figure else []) or sorted(directory.glob("figure.*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".svg":
            analysis["figure"] = path.read_text()
        else:
            data = base64.b64encode(path.read_bytes()).decode()
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            analysis["figure"] = f'<img src="data:{mime};base64,{data}" alt="">'
        return
    analysis["figure"] = ""


def collect(root):
    """Return the dashboard payload for a repository root."""
    analyses = {}
    for path in sorted((root / "analysis").glob("*/analysis.json")):
        analysis = read_json(path)
        if analysis and analysis.get("paper"):
            inline_figure(analysis, path.parent)
            analyses[analysis["paper"]] = analysis

    days = []
    for date_dir in sorted((root / "recommended").glob("[0-9]*-[0-9]*-[0-9]*"), reverse=True):
        papers = []
        for path in sorted(date_dir.glob("*/paper.json")):
            paper = read_json(path)
            if not paper:
                continue
            paper.setdefault("id", path.parent.name)
            paper["analysis"] = analyses.get(paper["id"])
            paper["datasets"] = (paper["analysis"] or {}).get("datasets", [])
            papers.append(paper)
        if not papers:
            continue

        days.append({"date": date_dir.name, "papers": papers})

    total = sum(len(day["papers"]) for day in days)
    ledger = f"recommended/ 에 {len(days)}일 누적" + (f" · 마지막 수집 {days[0]['date']}" if days else "")
    return {"meta": {"total_papers": total, "ledger": ledger}, "days": days}


def build():
    payload = json.dumps(collect(ROOT), ensure_ascii=False)
    # ponytail: </script> is the only sequence that can break out of the payload tag.
    OUTPUT.write_text(TEMPLATE.read_text().replace("__PAYLOAD__", payload.replace("</", "<\\/")))
    return payload


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as name:
        root = pathlib.Path(name)
        slug = root / "recommended" / "2026-08-19" / "a-paper"
        slug.mkdir(parents=True)
        (slug / "paper.json").write_text(json.dumps({"title": "A paper", "venue": "Nature"}))
        (root / "recommended" / "2026-08-18" / "empty").mkdir(parents=True)

        payload = collect(root)
        assert [day["date"] for day in payload["days"]] == ["2026-08-19"], "empty days are dropped, newest first"
        paper = payload["days"][0]["papers"][0]
        assert paper["id"] == "a-paper", "id falls back to the directory name"
        assert paper["analysis"] is None, "unanalysed papers stay pending"

        analysis = root / "analysis" / "7"
        analysis.mkdir(parents=True)
        (analysis / "analysis.json").write_text(
            json.dumps({"paper": "a-paper", "verdict": "적용 가능", "datasets": ["CheXpert"]})
        )
        payload = collect(root)
        paper = payload["days"][0]["papers"][0]
        assert paper["datasets"] == ["CheXpert"], "analysis is joined by paper id"
        assert payload["meta"]["total_papers"] == 1
        assert paper["analysis"]["figure"] == "", "a missing figure is not a broken image"

        (analysis / "figure.svg").write_text("<svg/>")
        assert collect(root)["days"][0]["papers"][0]["analysis"]["figure"] == "<svg/>", "svg is inlined as markup"

        (analysis / "figure.svg").unlink()
        (analysis / "figure.png").write_bytes(b"\x89PNG")
        figure = collect(root)["days"][0]["papers"][0]["analysis"]["figure"]
        assert figure == '<img src="data:image/png;base64,iVBORw==" alt="">', figure

    print("ok")


if __name__ == "__main__":
    demo() if "--check" in sys.argv else print(f"wrote {OUTPUT} ({len(build())} bytes of data)")
