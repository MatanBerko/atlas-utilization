# m0m1j0 spec investigation

Read-only investigation into what an "m0m1j0" histogram means under this repo's
actual naming convention, whether it's buildable from configuration, and what
BumpNet-compliance gaps exist. No pipeline code was run, changed, or executed.
All code quotes are from the repo at the branch point (`master`, commit
`0ae86dc`), file paths are repo-relative, line numbers are as read on disk.

---

## A. The naming convention

### A.1 — `LETTER_PARTICLE_MAPPING` (services/calculations/consts.py:28-35)

```python
LETTER_PARTICLE_MAPPING = {
    "e": "Electrons",
    "j": "Jets",
    "g": "Photons",
    "m": "Muons",
    "t": "Taus",
    "b": "BJets",
}
```

Exact meanings:

| Letter | Meaning |
|---|---|
| `e` | Electrons |
| `j` | Jets |
| `g` | Photons ("g" = gamma) |
| `m` | Muons |
| `t` | Taus |
| `b` | BJets (b-tagged jets, a collection distinct from `Jets`) |
| `l` | **Not present in this dict.** See A.5/A.6 — `l` ("lepton") appears only as an ad hoc, hand-written letter in two standalone analysis scripts, not as a key this repo's naming code recognizes. |

### A.2 — the histogram-name-assembling function

There are two separate naming functions in this repo, not one:

**(i) `prepare_im_combination_name`** — builds the intermediate SQLite/file
signature name for one *particle combination* (services/pipelines/im_pipeline.py:297-345):

```python
def prepare_im_combination_name(
    filename: str,
    final_state: str,
    combination: Dict,
) -> str:
    """
    Build the SQLite signature name for a given IM combination.
    ...
    """
    base_filename = filename.replace(".root", "")

    # Canonical particle order matches BumpNet convention
    PARTICLE_ORDER = [
        ("Electrons", "e"),
        ("Muons",     "m"),
        ("Jets",      "j"),
        ("BJets",     "b"),
        ("Photons",   "g"),
        ("Taus",      "t"),
    ]

    im_parts = []
    for ptype, letter in PARTICLE_ORDER:
        if ptype not in combination:
            continue
        value = combination[ptype]
        count = get_count(value)
        start = get_start(value)
        for idx in range(start, start + count):
            im_parts.append(f"{letter}{idx}")

    im_str = "".join(im_parts)   # e.g. "e0j0", "e1j0", "e0e1j0"
    return f"{base_filename}_FS_{final_state}_IM_{im_str}"
```

**(ii) `_convert_to_bumpnet_name`** — turns an `FS_.._IM_..` filename into the
final `mass_<combo>_cat_<fs>` BumpNet name (services/pipelines/histograms_pipeline.py:453-487):

```python
def _convert_to_bumpnet_name(fs_str: str, im_str: str) -> str:
    """
    Convert FS and IM strings to a BumpNet histogram name.
    ...
    """
    # IM part is already index-based — use directly as combo
    combo = im_str if im_str else "none"

    # FS part: count-based "2e_0m_3j_0g" → "2ex_0mx_3jx_0gx"
    fs_particles = re.findall(r'(\d+)([emjgtb])', fs_str)
    fs_formatted  = "_".join(f"{c}{p}x" for c, p in fs_particles)

    result = f"mass_{combo}_cat_{fs_formatted}"

    if 'cat' not in result and 'hCat' not in result:
        raise ValueError(
            f"Generated histogram name '{result}' doesn't contain 'cat' — "
            "BumpNet incompatible"
        )
    return result
```

The `_width_<bin_width>` suffix is added separately at histogram-creation time
(services/pipelines/histograms_pipeline.py:418-421):

```python
    histograms = []
    for bin_width in bin_widths_gev:
        nbins = max(1, math.ceil((global_max - global_min) / bin_width))
        hist_name = f"ROI_{hist_name_base}_width_{bin_width}"
```

**Important, verified discrepancy:** the ROOT `TH1F` object's own internal
name (the string ROOT stores as the histogram's key/title) always carries a
`ROI_` prefix — confirmed by three separate call sites building
`hist_name` this way (histograms_pipeline.py:364, 421, 568, 679) and by real
production output already in the repo, e.g.
`reports/cms_production_test/summary.md:27`:

```
`ROI_mass_e0j0_cat_1ex_0mx_1jx_1gx_1tx_0bx_width_10.0`
```

and `scripts/make_cms_report.py:41-43`, whose regex for parsing real produced
names requires the `ROI_` prefix:

```python
NAME_RE = re.compile(
    r"^ROI_mass_(?P<combo>[a-z0-9]+)_cat_"
    r"(?P<cat>(?:\d+[emjgtb]x_?)+)_width_(?P<w>[0-9.]+)$"
)
```

By contrast, the **output ROOT file name on disk** (when not using
`single_output_file`) omits `ROI_` (histograms_pipeline.py:530-531):

```python
                root_filename = f"{bumpnet_name}_hists.root"
```

So: the two examples given in the task prompt
(`mass_g0g1_cat_..._width_10.0`, `mass_l0l1l2l3_cat_..._width_3.0`) match the
**file-name-level `bumpnet_name`** convention, not the **actual ROOT
histogram object name**, which in every real, generic-pipeline-produced
example found in this repo carries a `ROI_` prefix. Separately (A.6 below),
both of the prompt's two examples turn out to be **hand-written literal
strings** in standalone scripts, not values actually produced by
`_convert_to_bumpnet_name` — so neither example is drawn from a real run of
the generic naming function either.

### A.3 — numeric suffixes: pT-ordering, descending, 0-indexed

Confirmed directly from the sort/slice code (services/calculations/physics_calcs.py:231-260):

```python
def slice_events_by_field(
    events: ak.Array,
    particle_counts: Dict,
    field_to_slice_by: str
) -> ak.Array:
    """
    Sort each particle type by field_to_slice_by (descending) and slice
    out the requested window [start : start + count].
    ...
    """
    for obj, value in particle_counts.items():
        ...
        count = get_count(value)
        start = get_start(value)

        obj_array = events[obj]
        sorted_obj_array = obj_array[ak.argsort(obj_array[field_to_slice_by], ascending=False)]
        # Slice window: [start : start + count]
        sliced_obj_array = sorted_obj_array[:, start : start + count]
        events[obj] = sliced_obj_array

    return events
```

`field_to_slice_by` defaults to `"pt"` (`domain/config.py:103`,
`MassCalculationConfig.field_to_slice_by: str = "pt"`). `ascending=False`
confirms descending-by-pT. Index `0` = highest pT (leading), `1` = second
highest (sub-leading), etc. — confirmed again in the docstring of
`prepare_im_combination_name` (im_pipeline.py:308-320):

```
    Examples (leading only, start=0):
        {"Electrons": (1, 0), "Jets": (1, 0)}       → IM_e0j0
        {"Electrons": (2, 0), "Jets": (1, 0)}       → IM_e0e1j0
        ...
    The name is unambiguous: IM_e1j0 always means sub-leading electron
    + leading jet (2-body invariant mass).
```

### A.4 — the complete name for "two leading muons + leading jet"

Combination dict: `{"Muons": (2, 0), "Jets": (1, 0)}`.

**Combo part** (from `prepare_im_combination_name`'s `PARTICLE_ORDER` —
Electrons, Muons, Jets, BJets, Photons, Taus, im_pipeline.py:325-332): Muons
before Jets, both leading (start=0) →

```
combo = "m0m1j0"
```

This confirms the prompt's own reading of the *combo fragment* is correct
under this repo's index-based convention: two leading muons = `m0m1`, one
leading jet = `j0`.

**cat_ block** — this is where the prompt's reading needs a caveat the
prompt could not have had: the `cat_` block is NOT derived from the
combination alone. It is derived from the **entire event's own final-state
particle multiplicities** — e/m/j/g/t/b counts, each capped at 4
(`_limit_particles_in_fs`, threshold=4, im_calculator.py:108-121 /
physics_calcs.py:86-98) — in the **fixed field order e, m, j, g, t, b**
(im_calculator.py:71-77 / physics_calcs.py:66-76):

```python
            all_events_fs = [
                f"{e}e_{m}m_{j}j_{g}g_{t}t_{b}b"
                ...
```

This is then formatted to `NeX_MmX_PjX_QgX_RtX_SbX` by `_convert_to_bumpnet_name`.

So a real "2 leading muons + leading jet" histogram, produced by the generic
pipeline naming function, does **not** have one fixed name — its `cat_`
block varies event-by-event with however many electrons/photons/taus/bjets
(and total jets) that specific event *also* contains, e.g.:

```
ROI_mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx_width_10.0   (event has exactly 2mu, 1jet, nothing else)
ROI_mass_m0m1j0_cat_0ex_2mx_3jx_0gx_0tx_0bx_width_10.0   (event has 2mu but 3 jets total)
ROI_mass_m0m1j0_cat_1ex_2mx_1jx_0gx_0tx_0bx_width_10.0   (event also has 1 electron)
... etc.
```

**If instead the repo's precedent for standalone-script naming is followed**
(A.6 below — a single, hand-picked, representative name, exactly as the
diphoton and 4-lepton scripts already do), the analogous single name, by the
same simplification pattern those scripts use (zero out every field not
in the combination, set the combination's own fields to its own counts),
would be:

```
mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx_width_<W>
```

— no `ROI_` prefix (matching the two precedent examples, which are file/base
names, not the internal ROOT object name). **This is an inference by pattern
match to precedent, not a value this repo's code would itself compute for
this specific 2-muon+1-jet combination** — flagged as such below.

**Field-by-field meaning of the `cat_` block**, confirmed from the regex/format
code above: each field is `<count><letter>x`, one per particle type, always in
order e, m, j, g, t, b (note: NOT the same order as the combo's own
`PARTICLE_ORDER`, which is e, m, j, b, g, t — see "BUGS OBSERVED" below for why
this asymmetry is worth flagging). `<count>` is the number of that particle
type present in the *whole event* (capped at 4). The trailing `x` is a fixed
literal character appended by the f-string `f"{c}{p}x"` (histograms_pipeline.py:478)
after every count+letter token — **its intended semantic meaning (if any) is
not documented or explained anywhere in this repo's code or comments**;
UNVERIFIED beyond "it is always present, always literal `x`, never a
variable". To verify intended meaning, would need to ask whoever wrote this
convention, or consult BumpNet's own documentation/source (arXiv:2501.05603
or its code), neither of which is in this repo.

**`width_` suffix**: the invariant-mass histogram's bin width in GeV, taken
verbatim from the `bin_width_gev` / `bin_widths_gev` config value and
formatted with Python's default float-to-string conversion (hence `10.0`,
not `10`) — confirmed at histograms_pipeline.py:420-421 quoted above.

### A.5 — precedent search for "m0m1j0" or any muon+jet histogram

```
grep -ri "m0m1j0" (whole repo, incl. git history via `git log -S`) → no matches
grep -ri "muon.*jet" combination-specific code/config → no matches beyond
    generic objects_to_calculate lists that include both Muons and Jets
    alongside every other type (e.g. config.yaml:136, config.cms_bjet_test.yaml:119)
```

`git log --all -S"m0m1j0"` returns nothing. No config file, script, report,
or CHANGES.md entry anywhere in this repo (tracked files or git history)
mentions `m0m1j0` or any muon+jet-specific combination by name. **There is no
precedent for this exact histogram in this repo.** The only true precedents
for *any* mixed-object (non-same-flavor) 2-body combination naming are the
generic-pipeline-produced `e0j0`, `j0g0`, `e0j0g0` etc. rows in
`reports/cms_production_test/summary.md` (e.g. lines 27-35) — those went
through the real `_convert_to_bumpnet_name` function, unlike the diphoton/
4-lepton precedents (A.6).

### A.6 — is "two leading muons plus the leading jet" confirmed, contradicted, or ambiguous?

**Partly confirmed, partly open** — split cleanly by which part of the name
is being asked about:

- The **combo fragment** `m0m1j0` = "two leading muons + leading jet" is
  **confirmed** by the naming code (A.2/A.4): under `PARTICLE_ORDER`, that
  combination dict deterministically produces exactly the string `m0m1j0`.
  Nothing else in this repo's convention produces that string. If the
  three-letter-fragment reading is all "m0m1j0" was ever meant to specify,
  it is correct.
- The **complete histogram name** is **ambiguous / open**, for a reason the
  prompt's reading could not anticipate: the `cat_` block is not determined
  by the combo alone, and this repo's own precedent for standalone scripts
  (diphoton, 4-lepton — scripts/higgs_diphoton_stage2_report.py:53,
  scripts/higgs_4lepton_zz_report.py:277-334,
  scripts/higgs_4lepton_clean_report.py:268-273) is to **hand-write a single
  literal name string**, not call the generic naming function at all — and
  the 4-lepton precedent's hand-written name uses a `cat_` block
  (`4lx_0jx_0gx_0tx_0bx`) that hard-codes `0jx` regardless of whatever jets
  a real 4-lepton event might also contain, i.e. that precedent's `cat_`
  block does **not** describe the true final-state multiplicity, it
  describes only the combination itself. Whether the m0m1j0 deliverable
  should follow that same simplification, or instead produce
  per-true-final-state names (which would multiply into many differently-
  named histograms), is a decision this repo's code does not make for you —
  see "STILL OPEN" below.

---

## B. Whether the combination is expressible from configuration alone

### B.1 — combinatorics.py: can "2 muons + 1 jet" come from config with no new code?

Yes, in the sense that `get_all_combinations` (services/calculations/combinatorics.py:41-105)
is a generic combination-generator entirely driven by its numeric parameters
(`min_particles`, `max_particles`, `min_count`, `max_count`,
`max_total_particles`, `object_types`) — it does not hard-code which particle
types pair together. A config block routed through
`MassCalculationConfig` (domain/config.py:94-149) such as:

```yaml
mass_calculation_task_config:
  objects_to_calculate: [Muons, Jets]
  min_particles_in_combination: 2
  max_particles_in_combination: 2
  min_count_particle_in_combination: 1
  max_count_particle_in_combination: 2
  max_total_particles_in_combination: 3
```

would, via `get_all_combinations(["Muons","Jets"], min_particles=2,
max_particles=2, min_count=1, max_count=2, max_total_particles=3)`, generate
(among others) the combination `{"Muons": (2, 0), "Jets": (1, 0)}` — i.e.
`m0m1j0` — with **zero new Python code**. (It would also generate every
other combination allowed by those bounds, e.g. `{"Muons": (1,0),
"Jets": (1,0)}` = `m0j0`, `{"Muons": (1,0), "Jets": (2,0)}` = `j0j1m0`
combo-order-adjusted, etc. — there is no config knob to request *only*
`m0m1j0` and nothing else from this function; you'd filter the generated
list afterward.)

**However** — this generic mass-calculation stage is exactly the stage
already established (per the task's own framing, and per
`scripts/higgs_diphoton_stage2_report.py:16-30`'s documented reason for
bypassing it) to be impractically slow at full scale. So while the answer to
"can config alone produce this combination" is yes, the practical answer for
this deliverable is B.3 below: it won't be produced this way.

### B.2 — domain/config.py: schema for object selections + prior guard

The two config surfaces relevant to object selection:

**Parse-time selection** (`ParsingConfig`, domain/config.py:30-91) —
`particle_counts` (per-collection min/max ranges) and `kinematic_cuts`
(pt/eta/phi/isolation/ID windows), both `Optional[dict]`, applied by
`services/parsing/event_selection.py::apply_parsing_event_selection` (see C.3).

**Mass-calculation-time combinatorics** (`MassCalculationConfig`,
domain/config.py:94-149) — `objects_to_calculate`,
`min/max_particles_in_combination`, `min/max_count_particle_in_combination`,
`max_total_particles_in_combination`, `include_subleading`,
`max_subleading_index`, all validated in `__post_init__` (domain/config.py:121-148).

**On "the production guard added there previously"**: I could not find any
guard in `domain/config.py` itself that is labeled, in a comment or commit
message, as "the production guard" — that exact phrase does not appear
anywhere in this repo (`git log --all --grep`, `grep -ri` both empty). The
closest actual validation guard physically located in `domain/config.py` is
in `ParsingConfig.__post_init__` (domain/config.py:87-91):

```python
        if not isinstance(self.enable_jet_tagging, bool):
            raise ValueError("enable_jet_tagging must be a boolean")
        if self.enable_jet_tagging and not self.jet_btagging_thresholds:
            # TODO add algorithm-specific validation
            raise ValueError("jet_btagging_thresholds must be specified when enable_jet_tagging is set")
```

introduced in commit `e988958` ("Allow for configuring BTagging discriminant
thresholds"). **UNVERIFIED** whether this is the specific guard meant — I'm
flagging it as the best candidate found, not asserting it's the one. To
verify, I would need you to point me at the guard you mean (a grep target,
commit hash, or PR).

There is, separately, a genuine combinatorics-specific guard, but it lives in
`combinatorics.py`, not `domain/config.py` — CHANGES.md:319-329, "Fix 9":

```python
                if sum(counts) < 2:                     # skip single-particle IM (physically meaningless)
                    continue
```

(combinatorics.py:85-86) — rejects any combination whose total particle count
is below 2. This does not block `m0m1j0` (3 particles total).

### B.3 — can the naming function be imported and reused by a standalone script?

**Technically importable, but with real friction, and — critically — not
what this repo's own precedent actually does.**

Two different functions could in principle be reused:

1. **`prepare_im_combination_name`** (services/pipelines/im_pipeline.py:297) —
   lighter-weight. Its module's imports (im_pipeline.py:1-17) are
   `sys, os, logging, typing, awkward, numpy`, plus
   `services.calculations.im_calculator.IMCalculator`,
   `services.calculations.combinatorics`, and
   `services.parsing.schemas.schema_needs_mev_to_gev_conversion` — no ROOT,
   no POSIX-only modules. Import path and signature:

   ```python
   from services.pipelines.im_pipeline import prepare_im_combination_name
   prepare_im_combination_name(filename: str, final_state: str, combination: Dict) -> str
   ```

   This builds the **intermediate** `..._FS_<fs>_IM_<combo>` name, not the
   final `mass_..._cat_..._width_...` BumpNet name.

2. **`_convert_to_bumpnet_name`** (services/pipelines/histograms_pipeline.py:453)
   — builds the actual `mass_<combo>_cat_<fs>` string, but its *module*
   (histograms_pipeline.py:1-18) imports `ROOT` (PyROOT, a heavy compiled
   dependency) and `fcntl` at the top level:

   ```python
   import fcntl
   ...
   import ROOT
   ```

   `fcntl` is POSIX-only — **this module cannot be imported on Windows at
   all** (`ModuleNotFoundError: No module named 'fcntl'`); it would need to
   run on the Linux cluster. Its name also has a leading underscore
   (`_convert_to_bumpnet_name`), the Python convention for "internal, not a
   public API" — nothing prevents importing it, but it signals the original
   authors did not intend external reuse. Import path and signature (Linux
   only, ROOT installed):

   ```python
   from services.pipelines.histograms_pipeline import _convert_to_bumpnet_name
   _convert_to_bumpnet_name(fs_str: str, im_str: str) -> str
   ```

   It expects `fs_str` in the count-based `"2e_0m_3j_0g"` form and `im_str`
   in the index-based `"m0m1j0"` form — both would need to be hand-assembled
   by the caller anyway (there's no single call that goes straight from a
   combination dict + event counts to the final name).

**But — precedent says don't.** The two analogous standalone scripts already
written for exactly this "bypass the slow generic stage" situation
(diphoton: `scripts/higgs_diphoton_stage2_report.py`; 4-lepton:
`scripts/higgs_4lepton_zz_report.py`, `scripts/higgs_4lepton_clean_report.py`,
`scripts/higgs_4lepton_partB_report.py`) do **not** import either naming
function. Checked their import blocks directly:

```
scripts/higgs_diphoton_stage2_report.py:39-46 → __future__, argparse, json, pathlib, numpy   (no services.* import)
scripts/higgs_4lepton_zz_report.py:41-47       → __future__, argparse, json, pathlib, numpy   (no services.* import)
scripts/higgs_4lepton_clean_report.py:25-36    → __future__, argparse, csv, json, sys, pathlib,
                                                  numpy, and names from higgs_4lepton_zz_report
                                                  (no services.pipelines.* import)
```

Instead they hard-code the finished name as a literal string
(`higgs_diphoton_stage2_report.py:53`: `BUMPNET_NAME =
"mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx"`; `higgs_4lepton_zz_report.py:323`:
`"mass_l0l1l2l3_cat_4lx_0jx_0gx_0tx_0bx_width_3.0"` passed directly as a
literal argument to `write_bumpnet_root`). So by this repo's own established
practice for this exact scenario, the answer to "should the naming function
be imported" is: **it has not been, twice, by the people who set the
precedent for this workaround** — they matched the convention by hand
instead. Whether to follow that precedent for m0m1j0, or to be the first
script to actually import and call `prepare_im_combination_name` /
`_convert_to_bumpnet_name`, is a choice, not something settled by the repo.

---

## C. Parsing and schema

### C.1 — Muon and Jet fields in the CMS NanoAOD schema

`services/parsing/schemas.py`, `RELEASE_SCHEMAS["cms-nanoaod"]["objects"]`
(lines 104-166):

```python
            "Muons": ["pt", "eta", "phi", "mass", "charge", "pfRelIso04_all", "looseId",
                      "sip3d", "dxy", "dz"],
            "Jets": ["pt", "eta", "phi", "mass"],
```

**Jet carries pt/eta/phi/mass** — confirmed, all four present
(schemas.py:155).

**`Jet_btagDeepFlavB`** — present, but not inside the `"Jets"` object list;
it's read as a separate "direct object" (schemas.py:37-39, 164):

```python
NANOAOD_BTAGGING_OBJECTS = [
    "Jet_btagDeepFlavB"
]
...
        "direct_objects": NANOAOD_BTAGGING_OBJECTS.copy(),
```

Confirmed via `file_parser.py`: it is always *read* from the file
(file_parser.py:224, 241: `direct_objects = schema_config.get("direct_objects",
[])` → `obj_branches.update({"DirectObjects": {k: k for k in
direct_objects}})`), but only *used* — to split `Jets` into `Jets`/`BJets` —
when `enable_jet_tagging=True` (file_parser.py:103-106):

```python
        if enable_jet_tagging:
            obj_events = FileParser._calculate_btagging_and_split(obj_events, jet_btagging_thresholds)
        # Strip out DirectObjects -- they are not physics objects!
        obj_events.pop("DirectObjects")
```

When `enable_jet_tagging=False` (the dataclass default,
`domain/config.py:58`), the branch is read then discarded every time —
present in the schema, inert unless explicitly turned on.

**Jet ID fields (`Jet_jetId`, `Jet_puId`, or any other jet-quality field)**:
**absent.** `grep -i "jetId\|puId"` across the whole repo returns zero
matches anywhere — not in `BASE_OBJECTS`, not in the `cms-nanoaod` schema's
`"objects"` block, not in `direct_objects`, not in any config YAML. No jet
quality/ID cut of any kind is applied anywhere in this pipeline.

### C.2 — RECORD_ID_TO_SCHEMA: the four specified records, checked one by one

`services/parsing/schemas.py:53-71`:

```python
RECORD_ID_TO_SCHEMA = {
    30529: "cms-nanoaod",  # /SingleElectron/Run2016G  NanoAODv9
    30562: "cms-nanoaod",  # /SingleElectron/Run2016H  NanoAODv9
    30530: "cms-nanoaod",  # /SingleMuon/Run2016G      NanoAODv9
    30563: "cms-nanoaod",  # /SingleMuon/Run2016H      NanoAODv9
    30521: "cms-nanoaod",  # /DoubleEG/Run2016G        NanoAODv9
    30554: "cms-nanoaod",  # /DoubleEG/Run2016H        NanoAODv9
    # H->ZZ->4l (analysis/higgs-4lepton-zz): registered before use, ...
    30522: "cms-nanoaod",  # /DoubleMuon/Run2016G      NanoAODv9
    30555: "cms-nanoaod",  # /DoubleMuon/Run2016H      NanoAODv9
    30528: "cms-nanoaod",  # /MuonEG/Run2016G          NanoAODv9
    30561: "cms-nanoaod",  # /MuonEG/Run2016H          NanoAODv9
}
```

Checked individually, as requested:

| Record | Meaning | Present? | Line |
|---|---|---|---|
| 30522 | /DoubleMuon/Run2016G | **Yes** — `"cms-nanoaod"` | schemas.py:67 |
| 30555 | /DoubleMuon/Run2016H | **Yes** — `"cms-nanoaod"` | schemas.py:68 |
| 30530 | /SingleMuon/Run2016G | **Yes** — `"cms-nanoaod"` | schemas.py:56 |
| 30563 | /SingleMuon/Run2016H | **Yes** — `"cms-nanoaod"` | schemas.py:57 |

All four are registered. The lookup function that would otherwise silently
misbehave on a missing entry is `get_release_year_for_record`
(schemas.py:587-616), whose `else` branch on a missing key
(schemas.py:614-616) raises rather than silently falling through:

```python
                raise ValueError(
                    f"Record ID {record_id} not found in RECORD_ID_TO_SCHEMA mapping. "
                    f"Available record IDs: {list(RECORD_ID_TO_SCHEMA.keys())}"
```

— so today, a missing entry would raise loudly, not silently yield zero
events; the historical bug the task references (four of six records silently
yielding zero events) is not reproducible with this current code for these
four records, since none of the four is missing.

### C.3 — the "at least 4 leptons" parse-time selection, and how to change it to "2 muons + 1 jet"

This is **not** a hard-coded Python condition — it's YAML-configured, applied
generically by `services/parsing/event_selection.py::apply_parsing_event_selection`
(lines 66-113), specifically the `combined_particle_counts` branch
(lines 104-111):

```python
    if combined_particle_counts:
        fields = [
            canonical_particle_field_name(f)
            for f in combined_particle_counts["fields"]
        ]
        events = physics_calcs.filter_events_by_combined_particle_count(
            events, fields, int(combined_particle_counts["min"])
        )
```

which calls `filter_events_by_combined_particle_count`
(services/calculations/physics_calcs.py:186-228) — sums per-event counts
across the listed collections and keeps events at or above `min`.

The actual "≥4" value lives in the tracked H→ZZ→4l config files, e.g.
`config.cms_higgs_4lepton_fullscale.yaml:145-147`:

```yaml
      combined_particle_counts:
        fields: [electrons, muons]
        min: 4
```

(same block, same values, in `config.cms_higgs_4lepton_validation.yaml:142-144`).

**To select "at least 2 muons and at least 1 jet" instead**: this is a
different, *already-existing*, and arguably simpler mechanism — the sibling
`particle_counts` block (event_selection.py:92-102, using
`filter_events_by_particle_counts` with `is_particle_counts_range=True`),
which applies **independent, AND-combined, per-collection** min/max ranges —
exactly "≥2 muons AND ≥1 jet", with no need for the OR/sum semantics
`combined_particle_counts` exists for (that mechanism was purpose-built for
"≥4 leptons of *any* e/mu mix", which is a different requirement — see
physics_calcs.py:196-203 docstring). The config change (not applied — spec
only, per instructions):

```yaml
  particle_counts:
    muons:
      min: 2
      max: 999      # or whatever practical cap
    jets:
      min: 1
      max: 999
```

placed in the same `parsing_task_config` location the H→ZZ→4l configs put
their `combined_particle_counts` block (i.e. under the relevant
`selection_by_record` entry or the global `particle_counts` key,
`ParsingConfig.particle_counts`, domain/config.py:62). No `combined_particle_counts`
block would be needed at all for this requirement.

### C.4 — loud-failure guard for a record's files mostly failing to open

Yes, present. `orchestration/handlers/parsing_handler.py:181-184` (threshold)
and 299-315 (the check itself):

```python
        # Above this fraction of a record's files failing to open, treat it as a
        # real failure rather than silently continuing with whatever (possibly
        # zero) events the surviving files produced -- see MAX_FILE_FAILURE_RATE.
        MAX_FILE_FAILURE_RATE = 0.20
```

```python
            # ---- Fail loudly instead of silently continuing with zero events ----
            # A record whose files mostly fail to open (network blip, bad
            # redirector, exhausted connection pool, ...) used to finish this
            # loop with near-zero retained events and no error -- indistinguishable
            # from a record that genuinely has low yield. Abort instead.
            ok_count, fail_count = file_counts[release_year]
            total_count = ok_count + fail_count
            if total_count > 0:
                failure_rate = fail_count / total_count
                if failure_rate > MAX_FILE_FAILURE_RATE:
                    raise RuntimeError(
                        f"Record {record_key}: {fail_count}/{total_count} files failed to "
                        f"open ({failure_rate:.0%} failure rate, exceeds the "
                        f"{MAX_FILE_FAILURE_RATE:.0%} threshold). Aborting this run rather "
                        f"than silently continuing with zero or near-zero events for this "
                        f"record."
                    )
```

Threshold: >20% of a record's files failing to open aborts the whole run
with a `RuntimeError`.

---

## D. Units and jet energy corrections

### D.1 — documented units and unit scaling

Yes, explicitly documented and code-enforced. `services/parsing/schemas.py:106`:

```python
        "native_pt_unit": "GeV",  # CMS NanoAOD; verified on real data (e-pair inv mass ~91 before any 1e-3 scaling)
```

The scaling decision function, `schema_needs_mev_to_gev_conversion`
(schemas.py:640-658):

```python
def schema_needs_mev_to_gev_conversion(release_year: str, record_id: int = None) -> bool:
    """
    Whether the invariant-mass stage must scale masses by 1e-3 (MeV -> GeV) for
    data from this release/schema.

    Driven by the schema's explicit ``native_pt_unit``. The conversion is
    skipped ONLY when the native unit is unambiguously "GeV". Everything else --
    "MeV", "unknown", an unmapped release, a missing/blank key, or a lookup
    failure -- keeps the historical behaviour of applying the conversion, so
    data is never silently left on the wrong scale.
    ...
    """
    if not release_year:
        return True
    return get_native_pt_unit(release_year, record_id=record_id).strip().lower() != "gev"
```

and the actual scaling operation, gated on that function
(services/pipelines/im_pipeline.py:48, 146-149):

```python
    apply_mev_to_gev = schema_needs_mev_to_gev_conversion(release_year)
...
def _convert_array_to_gev(inv_mass: ak.Array) -> ak.Array:
    """MeV -> GeV. Only valid for MeV-native releases; callers must gate this
    on schema_needs_mev_to_gev_conversion(release_year)."""
    return inv_mass * 1e-3
```

Net effect for CMS NanoAOD (`native_pt_unit: "GeV"`): `schema_needs_mev_to_gev_conversion`
returns `False`, so `Jet_pt`, `Jet_mass`, `Muon_pt`, `Muon_mass` are **not**
scaled by 1e-3 anywhere in the mass-calculation stage — they are used
as-read. This is the fix for the exact factor-of-1000 bug class the task
prompt references; the repo's own history and a report
(`reports/higgs_4lepton_zz/partB_review_summary.md:141-158`) explicitly
narrate that this earlier bug is why `native_pt_unit` exists per-schema at
all.

### D.2 — is NanoAOD Jet_pt already JEC'd? What does the repo assume?

**The repo makes no explicit statement either way**, and there is no
Jet-energy-correction code, comment, or config flag anywhere in this repo —
`grep -i "JEC\|jerc\|jet energy correct"` across all `.py` files returns zero
matches. This is a real gap, not just an oversight in my search: nothing in
the pipeline applies, undoes, or documents an assumption about jet energy
corrections.

**Local file check, as instructed (no download):** local `.root` files do
exist in `output/**/parsed_data/*.root` (e.g.
`output/cms_higgs_4lepton_fullscale_20260908_150157/parsed_data/parsed_record_30521_chunk0.root`),
but I inspected one directly with `uproot` (read-only, local file, no
network) and confirmed these are **not** raw/original CMS NanoAOD files —
they are this pipeline's own **already-reprocessed** output, re-zipped via
`ak.zip`/uproot's tree-writer into this project's internal schema. Their
branch titles are auto-generated ROOT leaflist strings, not CMS's original
branch documentation, e.g.:

```
Jets_pt   | title = Jets_pt[nJets]/F
Jets_mass | title = Jets_mass[nJets]/F
Muons_pt  | title = Muons_pt[nMuons]/F
```

(compare to the real, original NanoAOD titles already captured elsewhere in
this repo for *other* branches, e.g.
`reports/higgs_4lepton_zz/partB_review_summary.md:131`, `Electron_pt` /
`Muon_pt` → title `"p_{T}"` / `"pt"` — plain, uninformative, no unit, and
critically **no mention of JEC status** either.) No genuine raw NanoAOD
sample file (i.e. one retaining CMS's own original branch titles, as
delivered from CERN Open Data) exists locally on this machine.

**UNVERIFIED.** To verify whether `Jet_pt` is JEC-applied, you would need
either: (a) a genuine unprocessed NanoAOD ROOT file (its `Jet_pt` branch
title would need to be checked directly — though based on the pattern seen
for `Electron_pt`/`Muon_pt` above, CMS's own branch titles for kinematic
fields tend not to state correction status even on real files, so this may
not resolve it either), or (b) CMS's own NanoAOD content documentation for
the specific campaign (UL2016 NanoAODv9, per the record comments in
`RECORD_ID_TO_SCHEMA`) — not present in this repo, and out of scope for me
to assert from general knowledge per the task's evidence rule.

---

## E. BumpNet-compliance gaps

### E.1 — variable bin widths, or fixed only?

**Fixed width only, per individual histogram.** The `width_` field is a
literal, uniform GeV bin width. Confirmed by the `ROOT.TH1F` constructor call
itself (histograms_pipeline.py:422-423):

```python
        histograms.append(
            ROOT.TH1F(hist_name, hist_name, nbins, global_min, global_max)
        )
```

`TH1F(name, title, nbins, xmin, xmax)` is ROOT's *fixed*-bin-width
constructor (equal-width bins across `[xmin, xmax]`); ROOT does have a
variable-bin-edges constructor (`TH1F(name, title, nbins, edges_array)`) but
it is not used anywhere in this repo (`grep` for a `TH1F(...)` call passing
an array of edges: no matches). The repo **can** produce *several*
histograms at *different* fixed widths for the same combination
(`bin_width_gev` may be a list, histograms_pipeline.py:79-83), but each
individual histogram's bins are uniform.

### E.2 — Z-candidate collapsing (removing leptons that form a Z from the lepton list before combinatorics)?

**No — not implemented as the paper describes it, and this distinction
matters.** What exists is superficially similar but operates at a different
stage on different data:

`services/pipelines/post_processing_pipeline.py:47-69`, `_apply_z_peak_cut`:

```python
def _apply_z_peak_cut(
    arr: np.ndarray, signature: str, z_peak_cutoff: float, logger: logging.Logger
) -> np.ndarray:
    """
    Drop masses below ``z_peak_cutoff`` GeV for channels containing same-flavour dileptons.

    The array is returned untouched for every other
    channel and when the cut is disabled (cutoff <= 0).
    """
    if z_peak_cutoff <= 0:
        return arr
    if not _dilepton_flavor(signature):
        return arr
    kept = arr[arr >= z_peak_cutoff]
    ...
    return kept
```

This cuts on the **already-computed invariant-mass VALUE array** — it drops
mass values below `z_peak_cutoff` (default 115.0 GeV,
`PostProcessingConfig.z_peak_cutoff`, domain/config.py:162) for same-flavor
dilepton *signatures* (a mass-window cut on the final histogram content, to
keep the huge Z peak from dominating the peak-finding/binning logic
downstream — see the module docstring, post_processing_pipeline.py:3-10:
"Remove the Z-peak ... for peak detection").

This is a fundamentally different operation from the paper's Z-candidate
collapsing, which removes **lepton objects** from the per-event lepton list
**before** combinations are built, so that e.g. a 3-muon event where two
muons form a Z candidate has those two muons excluded from subsequent
combinatorics entirely. This repo's combinatorics/object-selection code
(`combinatorics.py`, `physics_calcs.py`, `event_selection.py`) has no
lepton-pairing, Z-mass-window object veto, or object-removal logic anywhere
— confirmed by `grep -i "z.candidate\|z_veto\|91\.2\|z boson"` across all
`.py` files, whose only hits are the four files already covered here (none
of which do object-level removal).

**Consequence, as you anticipated**: this repo's muon-muon-jet histogram is
*not* directly equivalent to the BumpNet paper's muon-muon-jet histogram —
in this repo, if the two leading muons happen to form a Z candidate, they
are still included in the `m0m1j0` combination; the paper would have
excluded/relabeled them before forming any combination at all.

### E.3 — jet relabeling by mass (standard/boosted-V/hadronic-top/high-mass)?

**No.** `grep` for jet-mass-based category boundaries (60/110/200 GeV,
"boosted", "hadronic top", "relabel") across all `.py` files: zero matches
anywhere in the repo. The only jet-splitting logic that exists at all is
b-tag-based (`_calculate_btagging_and_split`, gated by `enable_jet_tagging` +
`jet_btagging_thresholds`, C.1 above) — splitting `Jets` into `Jets`/`BJets`
by b-tag discriminant score, not by jet mass, and not into the paper's
four mass categories. Not present.

### E.4 — histogram preprocessing: dropping bins before the max, and excluding the first 10%?

**Half present.** "Dropping all bins before the histogram maximum" —
**yes**, implemented in two places:

`services/pipelines/histograms_pipeline.py:652-672`, `_apply_peak_removal_to_histogram`:

```python
def _apply_peak_removal_to_histogram(hist: ROOT.TH1F) -> None:
    """Zero all bins strictly before the rightmost highest bin."""
    nbins = hist.GetNbinsX()
    if nbins <= 0:
        return
    max_count = hist.GetMaximum()
    if max_count <= 0:
        return

    peak_bin_idx = None
    for bin_idx in range(nbins, 0, -1):
        if hist.GetBinContent(bin_idx) == max_count:
            peak_bin_idx = bin_idx
            break

    if peak_bin_idx is None or peak_bin_idx <= 1:
        return

    for bin_idx in range(1, peak_bin_idx):
        hist.SetBinContent(bin_idx, 0.0)
        hist.SetBinError(bin_idx, 0.0)
```

(gated by `apply_peak_removal_at_histogram_level`,
`HistogramCreationConfig`, domain/config.py:195 — off by default). A
second, independent implementation of essentially the same idea exists at
array level in the post-processing stage (`_find_rightmost_highest_peak` +
`filtered = arr[arr >= peak_mass]`, post_processing_pipeline.py:228-229,
312-332) as one of the module's five documented steps
(post_processing_pipeline.py:7-8: "Find the rightmost highest bin (peak)" /
"Remove data before the peak").

"Excluding the first 10% of bins" — **no**. `grep` for `0.1`, `10%`, or any
percentage-based bin-count exclusion in `services/**/*.py`: no genuine match
(`services/analysis/statistics_plotter.py:699`'s `0.1` is an unrelated plot
text-coordinate, not a bin-fraction). Not present anywhere.

### E.5 — usability criteria (>30 bins, ≥100 entries)?

**Implemented, but only as a post-hoc report check in standalone analysis
scripts — not enforced anywhere in the core pipeline.** Confirmed present in
three scripts (all descended from the diphoton/4-lepton precedent scripts
already discussed):

`scripts/higgs_diphoton_stage2_report.py:47-48`:
```python
BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100
```
used at lines 182-183, 231-232, 409-412 purely to print/record a `PASS`/`FAIL`
label in the generated report (`"meets_bin_bar": nbins > BUMPNET_MIN_BINS,
"meets_entry_bar": n_in >= BUMPNET_MIN_ENTRIES`) — it does not gate, drop, or
prevent writing any histogram. Same pattern, same two constants, in
`scripts/higgs_4lepton_zz_report.py:69-70` and referenced again in
`scripts/higgs_4lepton_clean_report.py:276-280`.

Searched the actual pipeline modules (`histograms_pipeline.py`,
`post_processing_pipeline.py`, `domain/config.py`) for any equivalent
gate/assertion: none found. So: the *numbers* 30 and 100 are known to this
codebase and match the task's stated criteria, but only as an
after-the-fact diagnostic in a few analysis scripts, never as something the
core pipeline checks or enforces before writing a histogram out.

---

## F. Optional — cluster storage listing

**Skipped.** Attempted a read-only SSH connection (`wipp-home`, the
configured jump-host alias) with a short timeout, per instructions not to
retry or troubleshoot. It failed immediately with "Could not resolve
hostname wipp-jump.weizmann.ac.il" — this session has no active Weizmann VPN
connection, so per the task's own instruction ("if the connection does not
come up immediately — just mark this section skipped and move on"), this
section is skipped. No listing of `/storage/agrp/berkom/atlas-utilization/output/`
was performed.

---

## BUGS OBSERVED, NOT FIXED

Per instructions, these are recorded only — nothing below was changed.

1. **`cat_` block field order does not match the combo's own `PARTICLE_ORDER`.**
   The combo part of a name (`prepare_im_combination_name`,
   im_pipeline.py:325-332) orders particle types
   Electrons, Muons, Jets, **BJets, Photons, Taus**. The `cat_` block
   (`_convert_to_bumpnet_name`'s `fs_particles` regex, and the FS-string
   builders in `im_calculator.py:71-77` / `physics_calcs.py:66-76`) orders
   them Electrons, Muons, Jets, **Photons, Taus, BJets** — Photons/Taus/BJets
   are in a different relative order between the two halves of the same
   histogram name. Not incorrect (each half is internally consistent and
   independently documented), just an inconsistency between two conventions
   used side-by-side in the same generated string.

2. **The two given example names (`mass_g0g1_cat_..._width_10.0`,
   `mass_l0l1l2l3_cat_..._width_3.0`) are not outputs of this repo's generic
   naming function** — they are literal Python string constants
   hand-written in `scripts/higgs_diphoton_stage2_report.py:53` and
   `scripts/higgs_4lepton_zz_report.py:277-334` /
   `scripts/higgs_4lepton_clean_report.py:268-273`. The 4-lepton one in
   particular uses the letter `l` for "lepton", which does not exist in
   `LETTER_PARTICLE_MAPPING` (A.1) and would not be produced by
   `prepare_im_combination_name`'s `PARTICLE_ORDER` (which has no combined
   "lepton" category — only separate `Electrons`/`Muons`). This isn't
   necessarily wrong for those two specific analyses, but it means the repo
   currently has two incompatible, un-reconciled "BumpNet naming
   conventions" in active use: the generic one
   (`services/pipelines/*_pipeline.py`) and the ad hoc one used by every
   standalone script written so far.

3. **The 4-lepton precedent's `cat_` block hard-codes `0jx`** (no jets)
   regardless of how many jets a real 4-lepton candidate event might also
   contain (`scripts/higgs_4lepton_zz_report.py:323`,
   `scripts/higgs_4lepton_clean_report.py:268,273`) — i.e. even in that
   precedent, the `cat_` block does not describe true per-event final-state
   multiplicity, only the combination's own particle types. This directly
   affects A.4/A.6's open question about what the m0m1j0 `cat_` block should
   contain, since the only two existing examples of this exact situation
   both chose to *not* reflect true event content there.

4. **No jet-quality/ID field is read or applied anywhere** (C.1) — no
   `Jet_jetId`, no `Jet_puId`, not in the schema, not in any cut. Any
   m0m1j0 jet could be a detector/pileup artifact with no ID requirement
   filtering it out. Whether that matters for this deliverable is a physics
   judgment call, not something I'm assessing here — just noting the gap
   exists in the current code, unconditionally, for every jet this pipeline
   has ever used.

5. **No jet-energy-correction handling or assertion anywhere** (D.2) — not
   necessarily wrong (NanoAOD's standard `Jet_pt` is commonly already the
   corrected value in CMS conventions generally, but this repo does not
   itself assert or verify that for the specific UL2016 NanoAODv9 samples
   in use, and I was not able to verify it from files available on this
   machine either).

---

## SETTLED BY THE REPOSITORY

- `LETTER_PARTICLE_MAPPING` contains exactly `e, j, g, m, t, b` → Electrons,
  Jets, Photons, Muons, Taus, BJets. `l` is not a key in this mapping
  anywhere in the core naming code.
- The numeric suffix in a combo token (`m0`, `m1`, `j0`, …) is a 0-indexed,
  descending-by-pT rank, confirmed by `slice_events_by_field`'s
  `ak.argsort(..., ascending=False)` and by `prepare_im_combination_name`'s
  own docstring.
- Under this repo's index-based naming convention, `{"Muons": (2,0),
  "Jets": (1,0)}` deterministically produces the combo fragment `m0m1j0` —
  the prompt's reading of "two leading muons + leading jet" as `m0m1j0` is
  correct for the combo part of the name.
- The `cat_` block is a per-event, capped-at-4, e/m/j/g/t/b final-state
  multiplicity description — NOT determined by the combination alone — when
  produced by the generic pipeline naming function.
- The real, generic-pipeline-produced ROOT histogram object name always
  carries a `ROI_` prefix; the output ROOT *file* name on disk does not.
  Both conventions coexist in this repo, verified from real production
  output already committed (`reports/cms_production_test/summary.md`).
- `m0m1j0` (or any muon+jet-specific combination) has no precedent anywhere
  in this repo's tracked files or git history.
- "2 muons + 1 jet" is fully expressible from `MassCalculationConfig`
  parameters alone via `get_all_combinations`, with no new Python code —
  though this generic stage is the one already established to be
  impractically slow at full scale for this project.
- All four requested record IDs (30522, 30555, 30530, 30563) are registered
  in `RECORD_ID_TO_SCHEMA`; a genuinely missing record ID would now raise a
  `ValueError` rather than silently yielding zero events.
- CMS NanoAOD `Jet_pt`/`Jet_eta`/`Jet_phi`/`Jet_mass` and
  `Muon_pt`/`eta`/`phi`/`mass` are all present in the schema; no MeV→GeV
  1e-3 scaling is applied to CMS NanoAOD data (native unit tracked as
  `"GeV"`, scaling explicitly gated off for it).
- `Jet_btagDeepFlavB` is present in the schema (read always, used only when
  b-tagging is enabled); no `Jet_jetId`/`Jet_puId` or any jet-quality field
  exists anywhere in this repo.
- The current "≥4 leptons" parse-time selection is YAML-configured
  (`combined_particle_counts`), not hard-coded; an independent, simpler,
  already-existing `particle_counts` mechanism (AND-combined, per-collection
  min/max) is the right tool for "≥2 muons AND ≥1 jet" — no
  `combined_particle_counts` needed for that requirement.
- A loud-failure guard aborts a parsing run if >20% of a record's files fail
  to open (`MAX_FILE_FAILURE_RATE = 0.20`, parsing_handler.py).
- Variable (non-uniform) bin widths are not supported — every histogram uses
  ROOT's fixed-bin-width `TH1F` constructor; only the *set* of widths tried
  per combination can vary.
- Z-candidate collapsing (paper-style, object-level, pre-combinatorics) is
  not implemented; what exists (`_apply_z_peak_cut`) is a different
  operation — a mass-window cut on already-computed invariant-mass values.
- Jet relabeling by mass (standard/boosted-V/hadronic-top/high-mass) is not
  implemented anywhere.
- "Drop all bins before the histogram maximum" is implemented (twice,
  independently, at histogram level and at array level). "Exclude the first
  10% of bins" is not implemented anywhere.
- The BumpNet usability bar (>30 bins, ≥100 entries) is known to this
  codebase (as literal constants, matching the task's numbers exactly) but
  is enforced only as a post-hoc PASS/FAIL label in a few standalone
  analysis-report scripts — never as a gate in the core pipeline.

## STILL OPEN — REQUIRES A HUMAN DECISION

1. **What should the m0m1j0 `cat_` block actually encode?**
   Either (a) the event's true final-state multiplicity (what the generic
   pipeline convention would produce, varying — potentially producing many
   differently-named histograms for what's conceptually "the same" m0m1j0
   selection, split by however many extra objects each event happens to
   have), or (b) a single fixed, representative block that zeroes out
   everything except the combination's own particle types (matching how the
   diphoton and 4-lepton precedent scripts already did it, e.g. the
   4-lepton precedent's hard-coded `0jx` regardless of true jet content).
   Branch (a) is more "correct" by the letter of the generic pipeline's own
   convention but produces a sprawl of histograms; branch (b) matches actual
   established practice in this repo (2-for-2 precedent) but means the name
   doesn't literally describe the event's full content. This choice
   directly determines the deliverable's filename(s).

2. **Should the standalone m0m1j0 script call
   `prepare_im_combination_name`/`_convert_to_bumpnet_name`, or hand-write
   the name like the diphoton/4-lepton scripts did?**
   Technically possible either way (B.3), but `_convert_to_bumpnet_name`'s
   module can't even be imported on Windows (`fcntl`), and both precedent
   scripts chose to hand-write. If hand-writing, the two known precedents
   disagree on `cat_` field completeness (open item 1), so there's no single
   template to copy exactly.

3. **Is a muon-muon-jet histogram from this repo comparable to the same
   histogram in the BumpNet paper at all**, given this repo does not
   implement Z-candidate collapsing (E.2)? If the two leading muons form a
   Z candidate, this repo's `m0m1j0` includes them anyway; the paper's
   methodology would not. Consequence: either (a) proceed without collapsing
   and treat the result as "this repo's own m0m1j0", not directly paper-
   equivalent, or (b) implement Z-candidate collapsing first (explicitly out
   of scope for this investigation and not touched).

4. **Jet energy correction status of `Jet_pt` remains genuinely unverified**
   (D.2) — no code, comment, or local raw sample file settles it. Either (a)
   obtain a real raw NanoAOD sample file (not the pipeline's own
   reprocessed output) and check its branch title/CMS documentation for the
   specific UL2016 NanoAODv9 campaign, or (b) proceed on an explicit,
   written assumption, accepting the risk that jets are off by whatever a
   JEC would have corrected.

5. **The "production guard" in `domain/config.py`** referenced in the task
   prompt could not be identified with certainty (B.2) — either (a) it's the
   `enable_jet_tagging`/`jet_btagging_thresholds` guard I found and flagged,
   or (b) it's something else I haven't located, in which case pointing me
   at a commit hash, PR, or grep target would resolve it in seconds.

6. **No jet-quality (`Jet_jetId`/`Jet_puId`) cut exists anywhere** (C.1,
   "BUGS OBSERVED" #4) — either (a) accept every jet in NanoAOD as-is for
   this deliverable, or (b) decide a jet ID cut is needed first (not
   implemented, would be new code, out of scope here).
