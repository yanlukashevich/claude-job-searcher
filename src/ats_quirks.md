# ATS quirks — recipes for forms we've already met

Read this **only** when the Apply click handed you off to an external ATS
(`applier_instructions.md` §3); on a portal's own form read `portal_quirks.md` instead. Each
recipe below was measured on a real run. Find your ATS, follow it, ignore the rest. If your ATS
isn't here, the rules in playbook §4–§7 are enough — and add a recipe here afterwards if you
learned something that isn't derivable from them.

---

## eRecruiter (`form.erecruiter.pl`)

Reached from a portal via Apply → new tab. On justjoin the on-page Apply refs can be duds;
the **top sticky "Apply" button** is the one that opens the ATS tab.

The form is Polish → answer in Polish (the CV language still follows the offer, §7).

1. **Cookie wall.** Dismiss OneTrust with **"Odrzuć wszystkie"** (privacy-preserving).
2. **Every dropdown is a custom React listbox, not a `<select>`** — Kraj, forma współpracy,
   oczekiwania finansowe, język, poziom. `form_input` does nothing on them. Open by `ref`,
   `find` the options, click by `ref`.
3. **The "Dodaj" trap (languages).** The button *commits* the current language **and spawns a
   fresh, empty, required "2. Język" row**. Either fill that trailing row too or delete it with
   its trash icon. An empty spawned row blocks submit with no visible error.
4. **Language-level labels vary by template.** Some instances show descriptive words, others
   show raw CEFR codes (A1–C2). Open the dropdown, read what's actually there, then map from
   `profile.md`'s CEFR table. Don't assume either style.
5. **Availability and work-mode are radios/checkboxes** → click by `ref`, verify the state.
6. **The message field** is usually "Dodatkowe uwagi" or "Informacje dodatkowe" (wording
   varies). Fill it with `form_input` — vision `type` dropped it twice here.
7. **Submit is "Wyślij"**, rendered grey but enabled. Check `.disabled` before treating it as
   a block.

---

## File input trapped in a same-origin `<iframe>` (seen on Symfonia HR)

**Symptom:** `find` / `read_page` only turn up an `<input type=text>` proxy — the accessibility
tree does not descend into the iframe, so you cannot see the real control.

**Do not** click the visible "choose file" button — it opens a native OS picker you cannot
operate.

**This is not a special case any more.** `mcp__webfile__attach_file` searches every frame of the
tab, so call it exactly as playbook §7 says; the string it returns ends with `(iframe frame)` when
the input it filled was in one. If several inputs match, `mcp__webfile__find_file_inputs` lists
them with their frame and the `nth` to use.

**Confirm** by the attached filename and size appearing on the form (e.g. `CV_….pdf (97kB)`).
