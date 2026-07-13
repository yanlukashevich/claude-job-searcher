# ATS quirks — recipes for forms we've already met

Read this **only** when the Apply button hands you off to an external ATS
(`applier_instructions.md` §6). Each recipe below was measured on a real run. Find your ATS,
follow it, ignore the rest. If your ATS isn't here, the principles in §6 are enough.

**What earns a section here:** a **widely-used ATS product** — one vendor's form that many
different employers use (eRecruiter, Workday, Avature, SmartRecruiters, Greenhouse, Lever,
Teamtailor, tomHRM …) — or a **general trap** any form can spring. **What does not:** one
company's homemade career page. Every applier pays for this file's length on every external
offer, so a recipe used on a single employer costs more than it returns. If a homemade form
teaches something form-general, put the lesson in *General traps* and don't name the company.

---

## General traps (any vendor)

### Hidden / off-DOM file input
**Symptom:** `file_upload` errors "Element is not a file input", or `find` only turns up an
`<input type=text>` proxy. The real input is `display:none`, sealed in a same-origin
`<iframe>`, or attached to `<body>` by a Dropzone widget — the accessibility tree does not
reach it, so `find` / `read_page` cannot see it. Seen on three unrelated vendors; assume it.

**Do not** click the visible "choose file" button — it opens a native OS picker you cannot
operate.

**Fix**, with `javascript_tool` (the page is same-origin and the file is the user's own):

1. Locate the real `input[type=file]` — search `document`, every same-origin
   `contentDocument`, and `<body>`'s own children. **Save its parent + next sibling.**
2. Give it an `id`; unhide it, and if it sits in an iframe, `document.body.appendChild(...)`
   it into the **top** document.
3. `find` it there and `file_upload` the CV onto that ref (this sets `input.files`).
4. Move it **back** to the saved parent/sibling; clear the temporary `id` and any styles.
5. Dispatch `input` then `change` on it so the page's own uploader runs natively.

**Confirm** by the attached filename and size appearing on the form (e.g. `CV_….pdf (97kB)`).

---

## eRecruiter (`form.erecruiter.pl`)

Reached from justjoin.it via Apply → new tab. On the justjoin page the on-page Apply refs can
be duds; the **top sticky "Apply" button** is the one that opens the ATS tab.

The form is Polish → answer in Polish, upload the PL CV.

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
7. **Salary is banded** → pick the band containing the profile figure.
8. **Submit is "Wyślij"**, rendered grey but enabled. Check `.disabled` before treating it as
   a block.

