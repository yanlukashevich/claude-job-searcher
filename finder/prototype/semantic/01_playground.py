r"""Stage 1: similarity playground. Text pairs in, cosine out. No data files.

Run:  .venv\Scripts\python.exe finder\prototype\semantic\01_playground.py
      ...\python.exe 01_playground.py --quiz    guess each score before it is revealed
      ...\python.exe 01_playground.py --repl    type your own pairs

The checkpoint is not "the numbers look nice" — it is that you can predict roughly
where a pair lands. --quiz is the checkpoint; the table is only the answer key.
"""

import sys

from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")  # Polish text vs the cp1252 console

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# (group, text_a, text_b, what we expect and why)
PAIRS = [
    ("cross-language bridge",
     "Programista Python", "Python Developer",
     "high — the whole premise; if this is low, nothing downstream works"),
    ("cross-language bridge",
     "Starszy inżynier oprogramowania", "Senior Software Engineer",
     "high — same claim, longer phrase"),
    ("cross-language bridge",
     "Analityk danych", "Data Analyst",
     "high — third title, to show the bridge is not one lucky pair"),
    ("cross-language bridge",
     "Praca zdalna", "Fully remote position",
     "LOW (0.16) — the bridge is title-shaped, not language-shaped; see FINDINGS.md"),
    ("cross-language bridge",
     "Praca zdalna", "Praca stacjonarna",
     "HIGH (0.80) — opposites, but both start 'Praca'; surface tokens beat meaning"),

    ("near-miss (the hard part)",
     "Python Developer", "Python Data Engineer",
     "close — same stack, different job; how close is the resolution limit"),
    ("near-miss (the hard part)",
     "Python Developer", "PHP Developer",
     "should be clearly below the pair above — shared shape, wrong stack"),
    ("near-miss (the hard part)",
     "AI Engineer", "Machine Learning Engineer",
     "very close — near-synonyms in this market"),
    ("near-miss (the hard part)",
     "Frontend Developer (React)", "Fullstack Developer (React, Node)",
     "close — frontend is a subset of the second"),
    ("near-miss (the hard part)",
     "Data Analyst", "Data Scientist",
     "close — the gap here predicts how much Stage 5 negatives must do"),
    ("near-miss (the hard part)",
     "Data Analyst", "Data Engineer",
     "0.83 — HIGHER than AI vs ML Engineer, which are synonyms. The shared\n"
     "            literal word 'Data' outweighs the actual synonymy. Read this twice."),

    ("far apart (sanity floor)",
     "Embedded C Developer", "Sales Manager",
     "low — establishes the floor for 'unrelated'"),
    ("far apart (sanity floor)",
     "Python Developer", "Truck driver",
     "0.09 — the true floor for 'unrelated'"),
    ("far apart (sanity floor)",
     "Python Developer", "Kierowca kat. C+E",
     "0.33 — 3x the floor, and not because of Polish: 'Kierowca ciezarowki'\n"
     "            scores 0.09. It is the literal 'C' colliding with C the language."),

    ("FAILURE MODE: no negation",
     "Java", "no Java, we use Python",
     "0.40 — lower than billed, but only because 15 extra tokens dilute a 1-token\n"
     "            query. Dilution, not logic. The controlled version is next."),
    ("FAILURE MODE: no negation",
     "we use Java", "we do not use Java",
     "0.77 — same length, one word 'not' apart. The NOT is nearly free."),
    ("FAILURE MODE: no negation",
     "remote work", "no remote work, on-site only",
     "0.75, vs 0.26 for 'on-site only' alone. Keeping the negated phrase in the\n"
     "            text is what scores; the 'no' does almost nothing."),
    ("FAILURE MODE: no numbers",
     "8000 PLN", "25000 PLN",
     "near-identical — no number sense; salary must stay arithmetic"),
    ("FAILURE MODE: no numbers",
     "2 years of experience", "10 years of experience",
     "near-identical — seniority must stay a boolean, not a similarity"),

    ("register asymmetry",
     "I want a remote Python job", "Python Developer",
     "a first-person wish vs a title — expect a penalty for the mismatch"),
    ("register asymmetry",
     "Senior Python Developer (Remote)", "Python Developer",
     "title vs title — should beat the wish above; this is why prototypes"),
    ("register asymmetry",
     "Python, Django, PostgreSQL, Docker", "Python Developer",
     "a bare tag list vs a title — the same penalty. Prototypes go in title register."),

    ("Yan's directions vs the rejects",
     "AI Engineer, LLM, RAG, PyTorch", "Machine Learning Engineer (LLM, LangChain)",
     "high — a wanted direction hitting its own offers"),
    ("Yan's directions vs the rejects",
     "AI Engineer, LLM, RAG, PyTorch", "Manual QA Tester, test cases, Jira",
     "low — wanted vs reject; this margin is what Stage 5 subtracts"),
    ("Yan's directions vs the rejects",
     "Python Developer", "Java Developer",
     "0.39 — stacks separate better than feared"),
    ("Yan's directions vs the rejects",
     "Python Developer", "Java Developer (Spring Boot)",
     "0.23 — the SAME pair, two words longer, scores 0.16 lower. Prototype\n"
     "            length moves the score on its own. Never compare across lengths."),
    ("Yan's directions vs the rejects",
     "Embedded C Developer", "Unity Game Developer (C#)",
     "watch this one too — both are 'C-ish' and neither is the other"),
]

QUERY_PAIRS = [(a, b) for _, a, b, _ in PAIRS]


def cosine(model, a, b):
    va, vb = model.encode([a, b], normalize_embeddings=True)
    return float(va @ vb)


def table(model):
    scores = {}
    group = None
    for g, a, b, note in PAIRS:
        if g != group:
            group = g
            print(f"\n{group}")
            print("-" * len(group))
        s = cosine(model, a, b)
        scores[(a, b)] = s
        print(f"  {s:5.3f}  {a!r}\n         {b!r}\n         -> {note}")
    return scores


def quiz(model):
    print("Guess the cosine (0..1) for each pair. Empty input skips. Ctrl-C quits.\n")
    errors = []
    for _, a, b, note in PAIRS:
        print(f"  A: {a}\n  B: {b}")
        try:
            raw = input("  your guess> ").strip().replace(",", ".")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        actual = cosine(model, a, b)
        if raw:
            try:
                guess = float(raw)
            except ValueError:
                print(f"  (not a number)  actual {actual:.3f}\n")
                continue
            err = abs(guess - actual)
            errors.append(err)
            print(f"  actual {actual:.3f}   off by {err:.3f}   {note}\n")
        else:
            print(f"  actual {actual:.3f}   {note}\n")
    if errors:
        print(f"pairs guessed: {len(errors)}   mean error: {sum(errors) / len(errors):.3f}")
        print("under ~0.08 means you have the model's scale in your head — checkpoint passed.")


def repl(model):
    print("Two lines per pair (blank line or Ctrl-C to quit).\n")
    while True:
        try:
            a = input("A> ").strip()
            if not a:
                break
            b = input("B> ").strip()
            if not b:
                break
        except (EOFError, KeyboardInterrupt):
            print()
            break
        print(f"   cosine = {cosine(model, a, b):.4f}\n")


if __name__ == "__main__":
    model = SentenceTransformer(MODEL)
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--quiz":
        quiz(model)
    elif arg == "--repl":
        repl(model)
    else:
        table(model)
        print("\nrerun with --quiz to test yourself, or --repl to try your own pairs.")
