import argparse
import json
import re
from pathlib import Path

import mwparserfromhell as mw
import pandas as pd

FIELD_MAP = {
    "Name": "name",
    "Kanji": "name_jp",
    "Romaji": "name_romaji",
    "Alias": "alias",
    "Nickname": "nickname",
    "Gender": "gender",
    "Race": "race",
    "Age": "age",
    "Birthday": "birthday",
    "Height": "height",
    "Weight": "weight",
    "Hair Color": "hair_color",
    "Eye Color": "eye_color",
    "Status": "status",
    "Occupation": "occupation",
    "Previous Occupation": "previous_occupation",
    "Affiliation": "affiliation",
    "Previous Affiliation": "previous_affiliation",
    "Relatives": "relatives",
    "Magic": "magic",
    "Authority": "authority",
    "Divine Protection": "divine_protection",
    "Affinity": "affinity",
    "Weapon": "weapon",
    "Equipment": "equipment",
    "Light Novel": "first_light_novel",
    "Manga": "first_manga",
    "Anime": "first_anime",
    "Game": "first_game",
    "Japanese Voice": "voice_jp",
    "English Voice": "voice_en",
}
IGNORED_FIELDS = {"Image", "Caption", "1"}

MAIN_SECTIONS = {
    "Appearance": "appearance",
    "Personality": "personality",
    "History": "history",
    "Abilities": "abilities_text",
}

SECTION_ALIASES = {"Apearance": "Appearance", "Ability": "Abilities"}
SKIP_SECTIONS = {"navigation", "references", "gallery"}


def tidy(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def clean_inline(value_wikitext):
    code = mw.parse(value_wikitext)
    for tag in code.filter_tags(matches=lambda t: str(t.tag).strip().lower() == "br"):
        try:
            code.replace(tag, " ; ")
        except ValueError:
            pass
    text = code.strip_code(normalize=True, collapse=True)
    text = text.replace("\n", " ")
    parts = [p.strip() for p in text.split(";")]
    seen, out = set(), []
    for p in parts:
        p = re.sub(r"\s+", " ", p)
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return " ; ".join(out)


def clean_block(code):
    return tidy(code.strip_code(normalize=True, collapse=True))


def find_infobox(code):
    for tpl in code.filter_templates(recursive=False):
        if str(tpl.name).strip().lower() == "character":
            return tpl
    return None


def link_titles(code):
    out, seen = [], set()
    for link in code.filter_wikilinks():
        title = str(link.title).split("#")[0].strip().replace("_", " ")
        if not title or re.match(r"(?i)^(file|image|category|media):", title):
            continue
        title = title[0].upper() + title[1:]
        if title not in seen:
            seen.add(title)
            out.append(title)
    return out


def category_names(code):
    out = []
    for link in code.filter_wikilinks():
        title = str(link.title).strip()
        if re.match(r"(?i)^category:", title):
            out.append(title.split(":", 1)[1].strip())
    return list(dict.fromkeys(out))


def strip_refs(wikitext):
    wikitext = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)
    wikitext = re.sub(r"<ref[^>/]*/>", "", wikitext)
    wikitext = re.sub(r"<ref[^>]*>.*?</ref>", "", wikitext,
                      flags=re.DOTALL | re.IGNORECASE)
    wikitext = re.sub(r"<gallery[^>]*>.*?</gallery>", "", wikitext,
                      flags=re.DOTALL | re.IGNORECASE)
    return wikitext


def parse_page(row):
    code = mw.parse(strip_refs(row["wikitext"]))
    infobox = find_infobox(code)
    if infobox is None:
        return None

    rec = {
        "page_id": row["page_id"],
        "url": row["url"],
        "last_revised": row["last_revised"],
        "scraped_at": row["scraped_at"],
    }
    extra = {}
    for param in infobox.params:
        key = str(param.name).strip()
        if key in IGNORED_FIELDS:
            continue
        value = clean_inline(str(param.value))
        if key in FIELD_MAP:
            rec[FIELD_MAP[key]] = value
        elif value:
            extra[key] = value
    rec["extra_json"] = json.dumps(extra, ensure_ascii=False) if extra else ""
    rec.setdefault("name", row["title"])

    rec["categories"] = " ; ".join(category_names(code))
    rec["linked_pages"] = " ; ".join(link_titles(code))

    code.remove(infobox)
    sections = code.get_sections(levels=[2], include_lead=True, flat=False)

    long_rows = []
    intro = ""
    for sec in sections:
        headings = sec.filter_headings()
        is_lead = not (sec.nodes and isinstance(sec.nodes[0], mw.nodes.Heading))
        if is_lead:
            paragraphs = [p for p in clean_block(sec).split("\n\n") if len(p) > 40]
            intro = paragraphs[0] if paragraphs else ""
            continue
        title = str(headings[0].title).strip()
        if title.lower() in SKIP_SECTIONS:
            continue
        sec.remove(headings[0])
        text = clean_block(sec)
        if not text:
            continue
        long_rows.append({"page_id": row["page_id"], "name": rec["name"],
                          "section": title, "text": text})
        col = MAIN_SECTIONS.get(SECTION_ALIASES.get(title, title))
        if col:
            rec[col] = text
    rec["intro"] = intro
    return rec, long_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="raw_pages.jsonl")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    chars, sections, skipped = [], [], []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            res = parse_page(row)
            if res is None:
                skipped.append(row["title"])
                continue
            chars.append(res[0])
            sections.extend(res[1])

    columns = (
        ["page_id", "name", "name_jp", "name_romaji", "alias", "nickname",
         "url"]
        + [c for c in FIELD_MAP.values()
           if c not in ("name", "name_jp", "name_romaji", "alias", "nickname")]
        + ["intro", "appearance", "personality", "history", "abilities_text",
           "categories", "linked_pages", "extra_json", "last_revised", "scraped_at"]
    )
    df = pd.DataFrame(chars).reindex(columns=columns)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "characters.csv", index=False, encoding="utf-8")
    pd.DataFrame(sections).to_csv(out / "character_sections.csv",
                                  index=False, encoding="utf-8")

    print(f"{len(chars)} personagens | {len(sections)} secoes | "
          f"{len(skipped)} paginas ignoradas (sem infobox Character)")
    print("\nPreenchimento por coluna:")
    filled = df.replace("", pd.NA).notna().sum().sort_values(ascending=False)
    for col, n in filled.items():
        print(f"  {col:22} {n:4}/{len(df)}")


if __name__ == "__main__":
    main()
