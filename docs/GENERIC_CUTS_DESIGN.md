# Generic per-object field and bit-mask cuts

This describes two optional, opt-in additions to the shared pipeline's
per-object kinematic-cut configuration: a numeric cut on an arbitrary
per-object field (`field_cuts`), and an integer bit-mask cut
(`bit_cuts`). Both default to off; every existing configuration is
unaffected. Written experiment-neutrally — neither capability is specific
to ATLAS or CMS.

## The problem

The pipeline's per-object kinematic cuts were, until now, limited to a
fixed, small set: a lower bound on transverse momentum (`pt_min`), a
symmetric bound on pseudorapidity (`eta_max`), a phi window
(`phi_min`/`phi_max`), and one experiment-specific relative-isolation cut
for electrons (`rel_isolation_max`). Two ordinary needs fall outside that
list entirely:

1. **A numeric cut on some other per-object field.** Any detector produces
   more per-object quantities than pt/eta/phi/isolation — an impact
   parameter, a shower shape, a working-point score, a second isolation
   variable computed differently from the one already wired in. There was
   no way to cut on any of them without adding bespoke code for each one.

2. **A bit-mask cut.** Some per-object quality fields are not a plain
   number or a boolean — they are an integer whose individual bits each
   encode a separate pass/fail decision (a jet identification working
   point is a common example: a jet quality flag stored as a small integer
   where bit 1 means "loose", bit 2 means "tight", and so on). The
   pipeline's existing boolean cuts (`bool_require`/`bool_any_of`)
   deliberately reject a non-0/1-valued integer field as a likely
   configuration mistake — correctly, since silently truthy-casting a
   multi-valued field would quietly do the wrong thing. That safety check
   meant there was no way to express a bit-mask cut at all, safely or
   otherwise.

## Config syntax

Both are nested under the existing per-object kinematic-cuts block,
alongside `pt_min`/`eta_max`/etc.

### `field_cuts` — numeric cut on an arbitrary field

```yaml
muons:
  pt_min: 20.0
  eta_max: 2.4
  field_cuts:
    pfRelIso04_all: { max: 0.15 }
    dxy:            { min: -0.2, max: 0.2 }
```

Each field gets its own `{min: ..., max: ...}` block; either bound may be
omitted, but at least one is required. Bound semantics match the existing
`pt_min`/`eta_max` implementation exactly: **`min` is inclusive
(`value >= min`), `max` is inclusive (`value <= max`)** — this was read
directly from `services/calculations/physics_calcs.py`'s existing pt/eta
handling, not chosen independently, so a mixed cut block behaves
consistently regardless of which fields are built-in and which are
generic.

Referencing a field auto-adds it to the set of branches read for that
object (if not already requested), logged once at INFO level so the
addition is never invisible. If the field turns out to be genuinely absent
from a given input file, that raises a loud, immediate error naming the
object, the field, and the file — never a silent no-op. A cut that quietly
does nothing changes a physics result with no signal that anything
happened; this is the deliberate opposite of that failure mode.

### `bit_cuts` — integer bit-mask cut

```yaml
jets:
  pt_min: 30.0
  eta_max: 2.5
  bit_cuts:
    jetId: { bits_all: 2 }     # (jetId & 2) == 2 -- every listed bit must be set
    puId:  { bits_any: 4 }     # (puId  & 4) != 0 -- at least one listed bit set
```

`bits_all: N` keeps an object where `(value & N) == N` (every bit set in
`N` must also be set in `value`). `bits_any: N` keeps an object where
`(value & N) != 0` (at least one bit set in `N` is also set in `value`).
Either or both may be given; if both are given, both must hold. The field
must be an integer type — a bit-mask cut on a float field raises a clear
error rather than silently truncating or misbehaving, since that
combination is almost certainly a configuration mistake.

**The mask is always an explicit integer value, never a bit index and
never a named working-point level.** This is deliberate, not an
omission: a bit *index* invites off-by-one mistakes (a "tight" working
point might be bit index 1, i.e. value `2`, and it is easy to write `1`
by mistake), and — more importantly — bit *meanings* are not stable
across data-taking years or reprocessing campaigns for the same
detector subsystem. A table mapping bit index or a named level to a
numeric value, for a given year or campaign, would have to live
somewhere, and would have to be kept current as new campaigns appear;
getting it wrong silently would look exactly like a normal, working
cut. Requiring the explicit integer value in config puts that
knowledge where the person who knows which campaign they are looking at
already has to be — and keeps the code itself completely ignorant of
any specific year, campaign, or working-point name. No such table exists
anywhere in this codebase, on either side of this addition, and none
should be added.

## Why `field_cuts` does not absorb `rel_isolation_max`

These remain two separate cuts on purpose. `rel_isolation_max` divides an
absolute isolation-energy field by the object's own transverse momentum,
inside the cut itself — it exists specifically because one experiment's
electron isolation is stored as an absolute cone energy, and the
*relative* quantity needed for the cut has to be computed by dividing by
pT. A detector that already stores its isolation as a relative quantity
(computed once, upstream, by the detector's own reconstruction) does not
need — and must not receive — a second division. Dividing an
already-relative quantity by pT again would compute a ratio of a ratio,
which is not a meaningful physical quantity. `field_cuts` therefore
performs a plain comparison against the field's own value, with no
division anywhere in it, and is not a generalization of
`rel_isolation_max` — the two coexist, are configured independently (see
Task D's validation, which sets both `rel_isolation_max` on electrons and
`field_cuts` in the same config block and confirms they act
independently), and neither absorbs the other.

## Evidence: existing configurations are unaffected

Every existing configuration — every ATLAS release and every CMS record
currently configured — was checked directly against this change, not
assumed to be fine:

- `config.yaml` (ATLAS): `kinematic_cuts` has no `field_cuts`/`bit_cuts`
  anywhere in it. The per-collection branch list this pipeline resolves
  (Electrons, Muons, Jets, Photons, Taus) was computed twice — once the
  way the pipeline resolved it before this change, once the way it
  resolves it after — and found **identical, field for field, in every
  collection**.
- `config.cms_hgg_data.yaml` (CMS): same check, same result — identical
  per-collection branch lists before and after, across all five
  collections checked, including the one collection (`Photons`) that
  already used the pre-existing `extra_object_fields` mechanism.
- The full existing test suite: 346 tests passed before this change; 394
  (346 plus 48 new tests for this change) pass after, with the exact same
  7 pre-existing, unrelated failures (a Windows-only file-locking issue at
  test-cleanup time) present in both runs, and no new failure introduced.

A configuration that never mentions `field_cuts` or `bit_cuts` — which is
every configuration that exists today — resolves to the exact same
`extra_object_fields` object it did before this change (not merely an
equal one — the identical object, unchanged), so nothing about branch
resolution, parsing, or selection can differ for it.

## Evidence: reproduces already-delivered physics

A separate, standalone script (`studies/m0m1j0_cms/selection.py`) already
implements both a numeric isolation cut and a bit-mask jet-ID cut by hand,
against real CMS data, and its results have already been delivered. That
script's own hand-written cuts were used as ground truth and compared
against this generic machinery on one real CMS file (5,000 events):

- **Muon isolation** (`field_cuts`): reproduced the hand-written cut
  exactly — the same 1,569 muons selected, and the per-muon selection
  mask identical for every single muon in the sample, with zero muons
  landing on any boundary where the two cuts' differing inequality
  conventions could have mattered.
- **Jet tight ID** (`bit_cuts`): the bit-mask logic itself reproduced the
  hand-written `(jetId & 2) != 0` condition exactly, with zero
  disagreement, once isolated from the separate `pt`/`eta` cuts. A small
  discrepancy (5 out of several thousand jets) appeared only in the full
  selection, once combined with the pipeline's own existing, unmodified
  `pt_min` cut — and was verified to be caused entirely by jets sitting
  exactly on the 30 GeV `pt` threshold, where this pipeline's
  already-established inclusive convention (`pt >= min`) differs from
  that one script's own independent choice of a strict inequality
  (`pt > min`). This is not a property of the new bit-mask capability,
  which is exact; it is a pre-existing fact about `pt_min`'s own
  convention, unrelated to and unchanged by this work.

Full detail, real numbers, and the plot are in
`studies/generic_cuts/VALIDATION.md`.

## Explicitly not part of this work

A third related capability — geometric (ΔR-based) overlap removal or
matching between two separate object collections — is a distinct,
separate capability, not implemented, stubbed, or designed for here. It
would need its own, independent design discussion.

## UNVERIFIED

- The exact `filterBits`/`jetId`-style bit-to-meaning mapping for any
  specific detector campaign is not, and should not be, encoded anywhere
  in this codebase (see "why bit meanings live in config, not code"
  above) — so there is nothing to verify here beyond what Task D already
  confirmed for the one campaign and one bit value it directly tested. A
  different campaign's bit meanings were not checked and would need their
  own confirmation before use, from that campaign's own documentation,
  each time.
- Task D's validation used one real file and 5,000 events, not the full
  dataset; the exact-match result for muon isolation and the
  bit-mask-isolated jet-ID result held throughout that sample, but a
  larger sample was not checked and could in principle surface a boundary
  case this sample did not happen to contain (as the jet `pt`-boundary
  case demonstrates already happening at this modest scale).
