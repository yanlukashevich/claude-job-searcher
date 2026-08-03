"""What holds one job together: the identity key, and the source list over a job's lifetime.

Both are easy to change and hard to eyeball. A normalizer that is slightly too eager silently
welds two employers into one; one that is slightly too shy re-forks every offer the next time
a portal changes its punctuation. The source lifecycle decides which link the cockpit shows
and whether an offer counts as expired.

Stdlib only, no framework -- like everything else here.

Usage:
  python finder/test_identity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harvest                                                      # noqa: E402
from common import clean_text, merge, norm_company, norm_title, offer_id  # noqa: E402

FAILED = []


def check(label, got, want):
    if got == want:
        print(f"  ok    {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL  {label}\n          got  {got!r}\n          want {want!r}")


def same(fn, a, b):
    check(f"{a!r} == {b!r}", fn(a), fn(b))


def differ(fn, a, b):
    if fn(a) != fn(b):
        print(f"  ok    {a!r} != {b!r}")
    else:
        FAILED.append(f"{a!r} != {b!r}")
        print(f"  FAIL  {a!r} and {b!r} both key to {fn(a)!r} -- two employers welded together")


print("company: spellings of one employer must key the same")
for a, b in [("LUX MED Sp. z o. o.", "LUX MED Sp. z o.o."),   # the space that started this
             ("NETIA S.A.", "Netia"),
             ("COMARCH", "Comarch SA"),
             ("Sii", "Sii Sp. z o.o."),
             ("P&P Solutions", "P&P Solutions Sp. z o.o."),
             ("UNITY-T GROUP sp. z o.o. sp.k.", "Unity-t Group Sp. z o.o. Sp.k."),
             ("TAURON Obsługa Klienta Sp. z o.o.", "TAURON Obsluga Klienta sp. z o.o.")]:
    same(norm_company, a, b)

print("company: different employers must NOT")
for a, b in [("Comarch", "Comarch Healthcare"), ("Netia", "Netia Data Center"),
             ("Box", "Boxo"), ("Reply Polska", "Reply Deutschland")]:
    differ(norm_company, a, b)

print("title: the same job written two ways")
for a, b in [("Tester Ferryt M/K", "Tester Ferryt (M/K)"),
             ("Programista / Programistka .NET", "Programista/Programistka .NET"),
             ("Tester/-ka Oprogramowania", "Tester/ka Oprogramowania"),
             ("Low - Code Developer", "Low-Code Developer"),
             ("Software Engineer (.NET)​ | f/m/d", "Software Engineer (.NET) | f/m/d")]:
    same(norm_title, a, b)

print("title: different jobs must NOT")
for a, b in [("C++ Developer", "C# Developer"),          # + and # survive normalization
             ("Frontend Developer", "Backend Developer"),
             ("Senior Java Developer", "Java Developer"),
             ("DevOps Engineer (UX/UI)", "DevOps Engineer")]:   # UX/UI is not a gender marker
    differ(norm_title, a, b)

print("ingest hygiene")
check("zero-width and nbsp", clean_text("Engineer​ (.NET) | f/m/d"),
      "Engineer (.NET) | f/m/d")

# ---- the source lifecycle --------------------------------------------------------------------

T = "Java Developer (k/m)"


def jj(slug, title=T, company="Acme Sp. z o.o."):
    return {"id": offer_id(title, company), "title": title, "company": company,
            "cities": ["Warszawa"], "skills": [],
            "sources": [{"site": "justjoin", "slug": slug,
                         "url": f"https://justjoin.it/job-offer/{slug}"}]}


def pr(gid, title=T, company="ACME sp. z o. o."):
    return {"id": offer_id(title, company), "title": title, "company": company,
            "cities": ["Warszawa"], "skills": [],
            "sources": [{"site": "pracuj", "slug": gid,
                         "url": f"https://www.pracuj.pl/praca/x,oferta,{gid}"}]}


def state(rows):
    """{(site, slug): archived?} for the single offer under test."""
    return {(s["site"], s["slug"]): bool(s.get("archived_at")) for s in rows[0]["sources"]}


def run(rows, *harvests, at, full=True):
    return merge(rows, [(site, {o["id"]: o for o in offs}) for site, offs in harvests],
                 at, archive_missing=full)


print("lifecycle: two portals, two spellings, one offer")
rows, s = run([], ("justjoin", [jj("a")]), ("pracuj", [pr("111")]), at="t1")
check("collapses to one row", len(rows), 1)
check("counted as linked", s["linked"], 1)
check("both links kept", state(rows), {("justjoin", "a"): False, ("pracuj", "111"): False})

print("lifecycle: justjoin re-posts under a new slug")
rows, s = run(rows, ("justjoin", [jj("b")]), ("pracuj", [pr("111")]), at="t2")
check("dead slug archived, new one live, old one kept",
      state(rows), {("justjoin", "a"): True, ("justjoin", "b"): False, ("pracuj", "111"): False})
check("offer itself still live", rows[0].get("archived_at"), None)

print("lifecycle: justjoin drops it, pracuj still carries it")
rows, s = run(rows, ("justjoin", []), ("pracuj", [pr("111")]), at="t3")
check("every justjoin link archived",
      state(rows), {("justjoin", "a"): True, ("justjoin", "b"): True, ("pracuj", "111"): False})
check("offer itself still live", rows[0].get("archived_at"), None)

print("lifecycle: the last portal drops it")
rows, s = run(rows, ("justjoin", []), ("pracuj", []), at="t4")
check("offer expires", rows[0].get("archived_at"), "t4")

print("lifecycle: it comes back")
rows, s = run(rows, ("justjoin", []), ("pracuj", [pr("111")]), at="t5")
check("expiry cleared", rows[0].get("archived_at"), None)
check("revival stamped", rows[0].get("revived_at"), "t5")

print("lifecycle: a --days partial run archives nothing")
rows, s = run(rows, ("justjoin", []), at="t6", full=False)
check("pracuj link untouched", state(rows)[("pracuj", "111")], False)

print("harvest: two spellings of one title inside ONE feed")
raw = [{"title": "QA/Automation Tester (Java)", "companyName": "SCALO", "slug": "s1",
        "locations": [{"city": "Wroclaw"}], "category": {"key": "testing"},
        "experienceLevel": "mid", "requiredSkills": [], "employmentTypes": [],
        "workplaceType": "remote", "publishedAt": "2026-07-30"},
       {"title": "QA Automation Tester (Java)", "companyName": "Scalo Sp. z o.o.", "slug": "s2",
        "locations": [{"city": "Krakow"}], "category": {"key": "testing"},
        "experienceLevel": "mid", "requiredSkills": [], "employmentTypes": [],
        "workplaceType": "remote", "publishedAt": "2026-07-29"}]
collapsed = harvest.collapse(raw)
check("one offer", len(collapsed), 1)
row = next(iter(collapsed.values()))
check("both apply links kept", sorted(s["slug"] for s in row["sources"]), ["s1", "s2"])
check("cities unioned", row["cities"], ["Krakow", "Wroclaw"])

print()
if FAILED:
    sys.exit(f"{len(FAILED)} FAILED: " + "; ".join(FAILED))
print("all pass")
