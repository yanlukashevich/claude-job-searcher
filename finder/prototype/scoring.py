"""The scorer. Code decides FACTS (keyword present / absent); the number only ORDERS offers.

This is the engine. You do not normally edit it -- you edit keywords.py. The one thing
worth knowing: a keyword hit in the TITLE counts double (the title names the job), the ROLE
table adds what the job IS (fullstack/backend/... vs analyst/manager/...), and two vetoes
throw an offer out when the title (or, soon, the skills) name someone else's stack.
"""
import re, unicodedata, collections
from keywords import KILL, CORE, CLOSE, UNKNOWN, OFF, WEIGHT, TITLE_KILL

# Polish 'l with stroke' is NOT decomposed by NFKD -- Wroclaw would become "wrocaw". Fold first.
FOLD = str.maketrans("łŁśŚźŹżŻćĆńŃóÓąĄęĘ", "llsszzzzccnnooaaee")

def norm(s):
    s = (s or "").translate(FOLD)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

# a title is prose, so each keyword needs a word-boundary regex -- and several collide.
TRAPS = {"java": r"\bjava\b(?!\s*script)", "go": r"\bgo(?:lang)?\b", ".net": r"(?<!asp)\.net\b",
         "react": r"\breact\b(?!\s*native)", "c++": r"\bc\+\+", "c#": r"\bc#"}
def pat(kw):
    return TRAPS.get(kw) or r"(?<!\w)" + re.escape(kw).replace(r"\ ", r"[\s\-/]") + r"(?!\w)"

# too short / too ambiguous to hunt for in prose. Skills field only.
SKILLS_ONLY = {"r", "c", "ai", "data", "ui", "api", "json", "excel", "windows", "rest",
               "cloud", "security", "testing", "qa", "network", "maintenance", "operations",
               "microsoft", "training", "communication", "automation", "architecture", "ml"}
# in CORE/OFF, but they say what the job DOES, not what it is built in. "Backend" must never
# rescue "Java Backend Developer" -- and the ROLE table below already pays for these, so a
# title keyword must NOT double-count them.
ROLE_WORDS = {"backend", "frontend", "microservices", "software development", "oop",
              "unit testing", "rest api", "restful api", "swagger", "devops", "deployment",
              "analytics", "documentation", "system architecture"}
CORE_TECH = {k for k in CORE if k not in ROLE_WORDS | SKILLS_ONLY}
OFF_TECH = {k for k in OFF if k not in ROLE_WORDS | SKILLS_ONLY}

TITLE_RX = [(re.compile(pat(k)), k, w) for b, w in WEIGHT
            for k in b if k not in SKILLS_ONLY | ROLE_WORDS]
KILL_RX = [(re.compile(pat(k)), k) for k in KILL if k not in SKILLS_ONLY]
TITLE_KILL_RX = re.compile(TITLE_KILL)      # a ROLE in the title: designer / security engineer
KNOWN = KILL | CORE | CLOSE | UNKNOWN | OFF

# what the job IS. The skills list never says this; only the title does.
ROLE = {r"\bfull[\s\-]?stack\b": 4, r"\bfront[\s\-]?end\b": 3, r"\bback[\s\-]?end\b": 3,
        r"\bweb\b": 2, r"\bsoftware (developer|engineer)\b": 2, r"\bprogramist": 2,
        r"\bdeveloper\b": 1, r"\bengineer\b": 1,
        r"\banalyst\b|\banalityk": -3, r"\bmanager\b|\bkierownik\b": -4,
        r"\bconsultant\b|\bkonsultant": -3, r"\barchitect\b|\barchitekt": -3,
        r"\bcoordinator\b|\bkoordynator": -3, r"\btrainer\b|\btrener\b": -4,
        r"\bspecialist\b|\bspecjalista\b": -1, r"\badministrator\b": -1}
SENIOR = re.compile(r"\b(senior|lead|principal|staff|head of|director|expert|vp)\b")
MID_OK = re.compile(r"\b(junior|mid|regular)\s*[/|\-]\s*(mid|senior|regular)|\bmid\b|\bjunior\b")

def hits(o):
    """(bucket -> [keyword]) over skills AND title, plus every part of the score."""
    t = norm(o["title"])
    h = collections.defaultdict(list)
    for s in o["skills"]:
        n = norm(s)
        for b, name in ((KILL, "KILL"), (CORE, "CORE"), (CLOSE, "CLOSE"),
                        (UNKNOWN, "UNKNOWN"), (OFF, "OFF")):
            if n in b:
                h[name].append(s)
    tkw = 0
    for rx, k, w in TITLE_RX:
        if rx.search(t):
            tkw += w * 2                      # the title names the job: double weight
            h["title:" + ("CORE" if w == 3 else "CLOSE" if w == 1 else
                          "UNKNOWN" if w == -1 else "OFF")].append(k)
    for rx, k in KILL_RX:
        if rx.search(t):
            h["KILL"].append(k + " (title)")
    m = TITLE_KILL_RX.search(t)
    if m:
        h["KILL"].append(m.group(0).strip() + " (role)")
    role = sum(v for rx, v in ROLE.items() if re.search(rx, t))
    sen = -8 if (SENIOR.search(t) and not MID_OK.search(t)) else 0
    sk = sum(w for s in o["skills"] for b, w in WEIGHT if norm(s) in b)
    return h, tkw, role, sen, sk

def veto(o):
    """An off-stack TECH in the title and no core TECH in the title -> it is another job."""
    t = norm(o["title"])
    off = [k for k in OFF_TECH if re.search(pat(k), t)]
    core = [k for k in CORE_TECH if re.search(pat(k), t)]
    return (bool(off) and not core), off

def matched(o):
    """How many of the offer's skills my vocabulary even recognises."""
    return sum(1 for s in o["skills"] if norm(s) in KNOWN)

BUCKETS = ["1_KILL", "2_VETO", "3_NEG", "4_WEAK", "5_PLAUS", "6_STRONG"]

def classify(o):
    """-> (bucket_name, score, why_text). The one place buckets are decided."""
    h, tkw, role, sen, sk = hits(o)
    tot = tkw + role + sen + sk
    if h["KILL"]:
        return "1_KILL", tot, "killed by " + ", ".join(sorted(set(h["KILL"]))[:3])
    if veto(o)[0]:
        return "2_VETO", tot, "title names " + ", ".join(veto(o)[1])
    b = ("3_NEG" if tot <= 0 else "4_WEAK" if tot < 5
         else "5_PLAUS" if tot < 10 else "6_STRONG")
    pos = h["CORE"] + h["title:CORE"] + h["CLOSE"] + h["title:CLOSE"]
    neg = h["OFF"] + h["title:OFF"] + h["UNKNOWN"] + h["title:UNKNOWN"]
    parts = [f"title{tkw:+} role{role:+}"]
    if sen:
        parts.append(f"senior{sen}")
    parts.append(f"skills{sk:+}")
    why = " · ".join(parts)
    if pos:
        why += "   +" + ",".join(dict.fromkeys(pos))
    if neg:
        why += "   −" + ",".join(dict.fromkeys(neg))
    return b, tot, why
