# justjoin.it offer API — notes for the harvester

Findings from scraping `https://justjoin.it/job-offers/all-locations/net?experience-levels=mid,junior`
on 2026-07-10. Written down so the harvester doesn't rediscover them.

> **The pagination/encoding traps below are live** — they apply to the current harvester,
> `finder/harvest.py`. The file names in older paragraphs (`offers_queue.json`,
> `build_worklist.ps1`, `harvest_offers.ps1`, once "in the project root") refer to the
> superseded PowerShell pipeline, now frozen in `legacy/`; read them as history.

## Don't scrape the DOM

The offer list is **virtualized *and* lazily paginated**. Only the cards near the viewport exist
in the DOM, and further pages load on scroll. A scroll-and-accumulate loop looks like it
finished long before it has: it stalled at **37 offers** when the real answer was **125**. There
is no scroll cadence that reliably fixes this — it is a race against a network fetch, and the
"no new cards for N ticks" heuristic silently lies.

Read the API instead. The page calls it itself; it is public (no auth, no cookie) and returns
exactly the fields we need.

## The endpoint

```
GET https://justjoin.it/api/candidate-api/offers
Accept: application/json
```

Query params, as used by the site for the URL above:

```
categories=net
experienceLevels=mid          # repeat the key for each level
experienceLevels=junior
sortBy=publishedAt
orderBy=descending
from=0                        # offset
itemsCount=50                 # page size
```

Response shape: `{ data: [...], meta: {...} }`

```jsonc
"meta": {
  "from": 0,
  "totalItems": 125,          // total BEFORE our title+company collapse
  "prev": { "cursor": null, "itemsCount": 50 },
  "next": { "cursor": 50,   "itemsCount": 50 }
}
```

### Pagination gotchas — two of them

- **`itemsPerPage` is ignored.** The real page-size param is **`itemsCount`**. Passing
  `itemsPerPage=100` silently returns the default 10.
- **`cursor` does not advance the page**, despite `meta.next.cursor` advertising it. Feeding
  `meta.next.cursor` back as `cursor=` returns page 1 again, forever. **`from=` (a plain integer
  offset) is what actually paginates.** A cursor loop looks like it works — it terminates, it
  dedups — and quietly yields only the first page.

Loop until `from + itemsCount >= meta.totalItems`.

### Useful fields on each `data[]` row

```
guid            slug            title           companyName
city            locations[]     isSuperOffer    isPromoted
experienceLevel category        workplaceType   employmentTypes
requiredSkills  niceToHaveSkills                publishedAt
applyMethod     expiredAt
```

Offer URL is `https://justjoin.it/job-offer/{slug}`.

`applyMethod` is worth inspecting when Phase 2 wants to route internal-modal vs external-ATS
offers before opening a browser at all.

## Multi-city duplicates — collapse on `title + companyName`

justjoin.it publishes **one job once per city**, each copy with its own `guid`, `slug` and URL.
They are genuinely distinct rows in the API and distinct cards on the site, which is why the
category header brags "253 offers".

For the mid+junior .NET filter: **125 rows → 119 real offers.** The 6 collapsed:

| offer | rows |
|---|---|
| `Backend Developer (.NET)` @ Andersen | 3 |
| `.NET Developer` @ emagine Polska | 3 (London, Lisbon, Brussels) |
| `.NET Developer` @ RITS Professional Services | 2 |
| `Software Developer` @ B2Bnetwork | 2 |

Note `guid` is **not** a dedup key here, and neither is `slug` or `url` — each city copy has its
own. The key is `title + companyName`, lowercased. Keep the first row (the feed is sorted
`publishedAt descending`, so that is the newest) and union the cities into `location`.

Also: a row's own `locations[]` array may already list several cities, independently of the
per-city duplication. Union `locations[].city` across every collapsed row, falling back to the
scalar `city` when `locations[]` is empty.

Applying to the same offer once per city would be embarrassing. This collapse is the point.

## Source data is dirty — do not trust it

Left as-is in `offers_queue.json` rather than silently "cleaned":

- Andersen lists both `Bosnia and herzegovina` and `Bosnia and Herzegovina` — same city, two
  casings, so a naive `Select-Object -Unique` keeps both.
- One Devapo row has a typo'd city, `krakw`.
- `city` is sometimes not a city: `Poland`, `Poland (Remote)`, `Hungary`.

If the harvester ever filters by city, it needs a normalization pass. It does not have one.

## PowerShell 5.1 traps — both cost a wrong file on disk

Hit both while writing `offers_queue.json`. They fail *quietly*, which is the dangerous part.

**1. `ConvertFrom-Json` does not enumerate a JSON array.** It emits the whole array as one
object down the pipeline. So this yields a 1-element array whose single element is the array:

```powershell
$existing = @(Get-Content $path -Raw | ConvertFrom-Json)   # WRONG: .Count -> 1
```

Assign first, then wrap:

```powershell
$parsed   = $raw | ConvertFrom-Json
$existing = @($parsed)                                      # .Count -> 6
```

The wrong version merged all 6 existing offers into a single malformed entry with array-valued
fields. `$existing.Count` printing `1` was the only clue.

**2. `Get-Content` decodes BOM-less UTF-8 as ANSI.** Read → re-write round-trips mangle the
Polish diacritics: `Inżynier` becomes `InĹĽynier`, `Wrocław` becomes `WrocĹ‚aw`. Read explicitly:

```powershell
$raw = [System.IO.File]::ReadAllText($path, (New-Object System.Text.UTF8Encoding $false))
```

and write the same way, so the file stays UTF-8 **without** a BOM:

```powershell
[System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding $false))
```

**`build_worklist.ps1` reads `offers_queue.json` and has not been audited for either trap.**

Corollary for verification: the PowerShell console *also* renders UTF-8 as ANSI, so mojibake in
terminal output does not prove corruption on disk — and clean-looking output does not prove the
absence of it. Verify by decoding the file's bytes as UTF-8 explicitly, not by eyeballing a
`Write-Host`.

## Output schema

`offers_queue.json` is a flat JSON array, UTF-8 no BOM, consumed by `build_worklist.ps1`:

```json
{
  "url": "https://justjoin.it/job-offer/{slug}",
  "title": "...",
  "company": "...",
  "location": "Kraków / Katowice",
  "stack": "dotnet",
  "status": "pending"
}
```

`location` joins collapsed cities with ` / `. If the applier ever needs a single city, that
decision belongs here, at harvest time — not in the prompt.

## Working script

`harvest_offers.ps1` (project root) does fetch → collapse → merge-by-url-and-key → backup →
write. It merges into the existing queue rather than overwriting, and dedups against what is
already there. Reasonable skeleton for the harvester; it currently hardcodes `categories=net`
and the two experience levels, and it is the script that produced the current
`offers_queue.json` (119 offers).
