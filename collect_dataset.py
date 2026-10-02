import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://rezero.fandom.com/api.php"
BASE_URL = "https://rezero.fandom.com/wiki/"
OUT = Path("raw_pages.jsonl")
BATCH = 50  

def make_session(email):
    s = requests.Session()
    s.headers["User-Agent"] = f"rezero-dataset-bot/1.0 ({email})"
    return s

def api(session, **params):
    params.update(format="json", formatversion=2)
    for attempt in range(4):
        try:
            r = session.get(API, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  erro ({e}); tentando de novo em {wait}s")
            time.sleep(wait)
    raise RuntimeError("API falhou depois de varias tentativas")


def list_category(session, category, recurse, delay):
    pages, seen_cats, queue = {}, set(), [category]
    while queue:
        cat = queue.pop()
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        cont = {}
        while True:
            data = api(
                session, action="query", list="categorymembers",
                cmtitle=f"Category:{cat}", cmlimit=500,
                cmtype="page|subcat", cmnamespace="0|14", **cont,
            )
            for m in data["query"]["categorymembers"]:
                if m["ns"] == 14:  
                    if recurse:
                        queue.append(m["title"].split(":", 1)[1])
                else:
                    pages[m["pageid"]] = m["title"]
            if "continue" not in data:
                break
            cont = data["continue"]
            time.sleep(delay)
        print(f"Categoria '{cat}': {len(pages)} paginas ate agora")
        time.sleep(delay)
    return pages

def fetch_batch(session, titles):
    data = api(
        session, action="query", titles="|".join(titles), redirects=1,
        prop="revisions", rvprop="content|timestamp", rvslots="main",
    )
    for p in data["query"]["pages"]:
        if p.get("missing") or "revisions" not in p:
            continue
        rev = p["revisions"][0]
        yield {
            "page_id": p["pageid"],
            "title": p["title"],
            "url": BASE_URL + p["title"].replace(" ", "_"),
            "wikitext": rev["slots"]["main"]["content"],
            "last_revised": rev["timestamp"],
            "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

def already_saved():
    if not OUT.exists():
        return set()
    with OUT.open(encoding="utf-8") as f:
        return {json.loads(line)["title"] for line in f if line.strip()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True, help="contato no User-Agent")
    ap.add_argument("--category", default="Characters")
    ap.add_argument("--no-recurse", action="store_true")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    session = make_session(args.email)
    pages = list_category(session, args.category, not args.no_recurse, args.delay)
    done = already_saved()
    todo = [t for t in pages.values() if t not in done]
    print(f"{len(pages)} paginas na categoria | {len(done)} ja salvas | {len(todo)} a baixar")

    with OUT.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            for row in fetch_batch(session, batch):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
            time.sleep(args.delay)
    print("Pronto:", OUT)


if __name__ == "__main__":
    main()
