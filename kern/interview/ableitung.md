# Where answers go (core)

Every answer has one place, so the same answers always produce the same files.

| ID | File | Field / section |
|---|---|---|
| R1, R2, R3 | `profil/rahmen.md` | `land`, `region`, `schulform` |
| R4 | `profil/rahmen.md` | `status` (`in_ausbildung` / `ausgebildet` / `quereinstieg`) + `status_begriff` (their term) |
| R5 | `profil/rahmen.md` | `ausbildung_ende`, section "Geplant ab" |
| R6 | `profil/lehrkraft.md` | `anrede`, `sprache` |
| U1, U2, U4 | `profil/lehrkraft.md` | table "Klassen und Fächer" |
| U3 | `profil/lehrkraft.md` | "Stundenraster" |
| U5 | `rahmen/<id>/kalender/<schuljahr>.md` | section "Schuleigene Termine" (status `geprüft`, because they stated it) |
| P1, P2 | `profil/pflichten.md` | one row per document type; a requirement names its issuer |
| P3 | `profil/lehrkraft.md` | table "Termine" |
| P6 | `eingang/` → skill `eingang` | |
| V1–V4 | `vorlagen/<typ>/herkunft.md` | one row per feature |

## Decisions
| Decision | Rule |
|---|---|
| Framework package id | `<country>-<region>-<schooltype>`: country as ISO code (`de`), region as official short code (`by`, `ni`, `nw`), school type in their term, lowercase ASCII. Without regions: `<country>-<schooltype>`. |
| Package | `rahmen/<id>/paket.md` exists → use it. Otherwise setup writes the index with every block `fehlt`; skill `recherche` fills it later. |
| Training rules | `status = in_ausbildung` → the package's `ausbildung.md` (once researched) is read for visit and exam documents; otherwise never. |
| Areas | one per class × subject: `bereiche/<klasse>-<fach>/STAND.md`; sub-folders are created when the first file needs them. |
| Template | only from their example (`vorlage-ableiten`); a feature is a `Vorgabe` only with a named issuer, otherwise `Vorliebe` or `Beispiel`. Without an example: the core design reference. |
| Requirements | what school or seminar asks for is a row in `profil/pflichten.md` and is never dropped silently. |
