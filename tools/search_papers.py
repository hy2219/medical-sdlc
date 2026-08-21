#!/usr/bin/env python3
"""Search a fixed set of venues for recent papers, in parallel, without any login.

The venue list is weighted towards where a clinician actually reads: general
medicine and radiology journals first, then the few method venues whose work
reaches imaging practice. Pure machine-learning venues are deliberately thin —
a paper a radiologist cannot act on is noise here, however strong the method.

Two public APIs cover the list. OpenAlex indexes the journals with stable
identifiers and full abstracts. The conferences are a different story:
OpenAlex only carries their older proceedings, while recent accepted papers
appear on arXiv within days and say so in the comment field, so that is where
we look.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from concurrent.futures import ThreadPoolExecutor

# ponytail: OpenAlex asks for a contact address and gives the polite pool in return.
MAILTO = "medical-sdlc@example.com"

# Each journal is a name to search OpenAlex sources for, plus the pattern a source
# must match. The pattern keeps "Nature" from also matching "Nature Genetics".
JOURNALS = {
    "Nature": r"^nature$",
    "Nature Medicine": r"^nature medicine$",
    "Nature Communications": r"^nature communications$",
    "Nature Biomedical Engineering": r"^nature biomedical engineering$",
    "npj Digital Medicine": r"^npj digital medicine$",
    "The Lancet Digital Health": r"^(the )?lancet digital health$",
    "Radiology": r"^radiology$",
    "Radiology: Artificial Intelligence": r"^radiology[:.]?\s*artificial intelligence$",
    "European Radiology": r"^european radiology$",
    "Medical Image Analysis": r"^medical image analysis$",
}

CONFERENCES = ["MICCAI", "IPMI", "CVPR", "NeurIPS", "ICLR"]

ATOM = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}


def fetch(url, **params):
    query = urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            # Both APIs rate-limit bursts; backing off is cheaper than searching less.
            if error.code not in (429, 503) or attempt == 3:
                raise
            time.sleep(2**attempt)


def openalex(path, **params):
    return json.loads(fetch(f"https://api.openalex.org/{path}", mailto=MAILTO, **params))


def source_ids(journal, pattern):
    found = openalex("sources", search=journal, per_page=200)["results"]
    return [
        s["id"].rsplit("/", 1)[-1]
        for s in found
        if re.search(pattern, s["display_name"].strip(), re.I)
    ]


def flatten_abstract(inverted):
    if not inverted:
        return ""
    return " ".join(w for _, w in sorted((i, w) for w, ii in inverted.items() for i in ii))


def search_journal(journal, pattern, query, start, end, limit):
    ids = source_ids(journal, pattern)
    if not ids:
        return []
    works = openalex(
        "works",
        search=query,
        filter=",".join([
            f"from_publication_date:{start}",
            f"to_publication_date:{end}",
            "primary_location.source.id:" + "|".join(ids),
        ]),
        per_page=min(limit, 200),
        sort="relevance_score:desc",
    )["results"]
    return [
        {
            "title": w.get("title") or "",
            "authors": [a["author"]["display_name"] for a in w.get("authorships", [])][:12],
            "venue": journal,
            "date": w.get("publication_date"),
            "citations": w.get("cited_by_count", 0),
            "source": "OpenAlex",
            "url": w.get("doi") or w.get("id"),
            "abstract": flatten_abstract(w.get("abstract_inverted_index")),
        }
        for w in works
    ]


def search_conference(venue, query, start, end, limit):
    """arXiv papers whose comment or journal reference names this conference."""
    window = f"[{start.replace('-', '')}0000 TO {end.replace('-', '')}2359]"
    feed = fetch(
        "http://export.arxiv.org/api/query",
        search_query=f'abs:"{query}" AND (co:{venue} OR jr:{venue}) AND submittedDate:{window}',
        max_results=limit,
        sortBy="submittedDate",
        sortOrder="descending",
    )
    entries = ElementTree.fromstring(feed).findall("a:entry", ATOM)
    return [
        {
            "title": " ".join(e.findtext("a:title", "", ATOM).split()),
            "authors": [a.findtext("a:name", "", ATOM) for a in e.findall("a:author", ATOM)][:12],
            "venue": venue,
            "date": e.findtext("a:published", "", ATOM)[:10],
            "citations": 0,
            "source": "arXiv",
            "url": e.findtext("a:id", "", ATOM),
            "abstract": " ".join(e.findtext("a:summary", "", ATOM).split()),
        }
        for e in entries
    ]


def guarded(label, search):
    try:
        return search()
    except (urllib.error.URLError, TimeoutError, ElementTree.ParseError) as error:
        # One unreachable venue must not sink the whole search.
        print(f"{label}: {error}", file=sys.stderr)
        return []


def search(query, start, end, limit=25):
    """Search every venue at once, newest first, deduplicated across the two APIs."""
    tasks = [
        (journal, lambda j=journal, p=pattern: search_journal(j, p, query, start, end, limit))
        for journal, pattern in JOURNALS.items()
    ] + [
        (venue, lambda v=venue: search_conference(v, query, start, end, limit))
        for venue in CONFERENCES
    ]

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        batches = pool.map(lambda task: guarded(*task), tasks)

    seen, papers = set(), []
    for batch in batches:
        for item in batch:
            key = re.sub(r"\W+", "", item["title"]).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            papers.append(item)
    papers.sort(key=lambda p: (p["date"] or "", p["citations"]), reverse=True)
    return papers


def demo():
    assert flatten_abstract({"deep": [1], "A": [0], "model": [2]}) == "A deep model"
    assert flatten_abstract(None) == ""
    for journal, pattern in JOURNALS.items():
        assert source_ids(journal, pattern), f"{journal} must resolve to an OpenAlex source"
    assert guarded("unreachable venue", lambda: (_ for _ in ()).throw(TimeoutError())) == []

    papers = search("medical imaging", "2025-01-01", "2026-12-31", limit=5)
    assert papers, "the venue search returned nothing at all"
    venues = {p["venue"] for p in papers}
    assert venues & set(CONFERENCES), f"no conference papers, only {venues}"
    assert venues & set(JOURNALS), f"no journal papers, only {venues}"
    assert len({p["title"] for p in papers}) == len(papers), "duplicate titles survived"
    print(f"ok: {len(papers)} papers from {len(venues)} venues")


if __name__ == "__main__":
    if "--check" in sys.argv:
        demo()
    else:
        query, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
        print(json.dumps(search(query, start, end), ensure_ascii=False, indent=1))
