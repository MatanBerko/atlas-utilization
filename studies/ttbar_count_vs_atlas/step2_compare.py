#!/usr/bin/env python
"""
Step 2 (ttbar_count_vs_atlas), part 2: compare the two enumerations produced
by step2_enumerate.py and emit the evidence JSON + the markdown table.

Reads step2_ours.json and step2_pr31.json (each written by a run of
step2_enumerate.py inside its own repo) and reports:

  * the two total pattern counts,
  * the per-category combination counts side by side,
  * EVERY category where the two combination SETS differ, with the
    differing combinations listed explicitly.
"""
import argparse
import json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ours", required=True)
    p.add_argument("--pr31", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-md", required=True)
    args = p.parse_args()

    with open(args.ours) as fh:
        ours = json.load(fh)
    with open(args.pr31) as fh:
        pr31 = json.load(fh)

    all_cats = sorted(set(ours["categories"]) | set(pr31["categories"]),
                      key=lambda s: tuple(int(x[:-1]) for x in s.split("_")))

    rows = []
    diffs = []
    for cat in all_cats:
        o = set(ours["categories"].get(cat, []))
        p31 = set(pr31["categories"].get(cat, []))
        rows.append({
            "category": cat,
            "n_ours": len(o),
            "n_pr31": len(p31),
            "equal": o == p31,
        })
        if o != p31:
            diffs.append({
                "category": cat,
                "n_ours": len(o),
                "n_pr31": len(p31),
                "only_in_ours": sorted(o - p31),
                "only_in_pr31": sorted(p31 - o),
            })

    combos_o = set(ours["combinations"])
    combos_p = set(pr31["combinations"])

    result = {
        "ours_repo_head": ours.get("repo_head", ""),
        "pr31_repo_head": pr31.get("repo_head", ""),
        "ours_config": ours["config"],
        "pr31_config": pr31["config"],
        "ours_config_source": ours["config_source"],
        "pr31_config_source": pr31["config_source"],
        "ours_containment_function": ours["containment_function"],
        "pr31_containment_function": pr31["containment_function"],
        "ours_fs_label_example": ours["fs_label_example"],
        "pr31_fs_label_example": pr31["fs_label_example"],
        "n_combinations_ours": ours["n_combinations"],
        "n_combinations_pr31": pr31["n_combinations"],
        "combination_pattern_sets_identical": combos_o == combos_p,
        "combination_patterns_only_in_ours": sorted(combos_o - combos_p),
        "combination_patterns_only_in_pr31": sorted(combos_p - combos_o),
        "n_categories_ours": ours["n_categories"],
        "n_categories_pr31": pr31["n_categories"],
        "n_categories_compared": len(all_cats),
        "n_categories_with_differing_combination_sets": len(diffs),
        "configs_identical": ours["config"] == pr31["config"],
        "per_category": rows,
        "differences": diffs,
    }
    with open(args.out_json, "w") as fh:
        json.dump(result, fh, indent=1)

    total_o = sum(r["n_ours"] for r in rows)
    total_p = sum(r["n_pr31"] for r in rows)

    lines = []
    lines.append("# Step 2 - combination counts per category: ours vs upstream PR #31")
    lines.append("")
    lines.append("Produced by RUNNING both codebases (`step2_enumerate.py` once per repo, then")
    lines.append("`step2_compare.py`). Each side used its OWN `get_all_combinations` and its own")
    lines.append("final-state containment function; nothing was shared between the two runs.")
    lines.append("")
    lines.append(f"* our checkout head: `{result['ours_repo_head']}`")
    lines.append(f"* PR #31 head: `{result['pr31_repo_head']}` (upstream `refs/pull/31/head`, read-only)")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append("| quantity | ours | PR #31 |")
    lines.append("|---|---:|---:|")
    lines.append(f"| combination patterns generated | {result['n_combinations_ours']} | {result['n_combinations_pr31']} |")
    lines.append(f"| categories enumerated | {result['n_categories_ours']} | {result['n_categories_pr31']} |")
    lines.append(f"| sum over categories of combinations allowed | {total_o} | {total_p} |")
    lines.append(f"| categories whose combination set differs | {len(diffs)} | {len(diffs)} |")
    lines.append("")
    lines.append(f"Combination pattern sets identical: **{result['combination_pattern_sets_identical']}**.  ")
    lines.append(f"Combinatorics configs identical: **{result['configs_identical']}**.")
    lines.append("")
    lines.append("Config actually used by each side:")
    lines.append("")
    lines.append("| parameter | ours | PR #31 |")
    lines.append("|---|---|---|")
    for k in sorted(set(result["ours_config"]) | set(result["pr31_config"])):
        lines.append(f"| `{k}` | `{result['ours_config'].get(k)}` | `{result['pr31_config'].get(k)}` |")
    lines.append("")
    lines.append(f"* ours config read from: {result['ours_config_source']}")
    lines.append(f"* PR #31 config read from: {result['pr31_config_source']}")
    lines.append(f"* ours containment: `{result['ours_containment_function']}`")
    lines.append(f"* PR #31 containment: `{result['pr31_containment_function']}`")
    lines.append(f"* final-state label shape, 1e/2mu/3j/1b: ours `{result['ours_fs_label_example']}`, "
                 f"PR #31 `{result['pr31_fs_label_example']}`")
    lines.append("")
    lines.append("## Categories where the combination sets differ")
    lines.append("")
    if not diffs:
        lines.append("**None.** Every one of the "
                     f"{len(all_cats)} categories allowed by the rule gets exactly the same set of")
        lines.append("invariant-mass combinations from both codebases.")
    else:
        for d in diffs:
            lines.append(f"### `{d['category']}` - ours {d['n_ours']}, PR #31 {d['n_pr31']}")
            lines.append("")
            if d["only_in_ours"]:
                lines.append("Only in ours: " + ", ".join(f"`{c}`" for c in d["only_in_ours"]))
            if d["only_in_pr31"]:
                lines.append("Only in PR #31: " + ", ".join(f"`{c}`" for c in d["only_in_pr31"]))
            lines.append("")
    lines.append("")
    lines.append("## Per-category combination counts (all "
                 f"{len(all_cats)} categories)")
    lines.append("")
    lines.append("`j` is the LIGHT-jet count. For PR #31 `4j` means exactly 4; for us `4j` is the")
    lines.append("display-capped label for 4 OR MORE light jets. That difference changes which")
    lines.append("EVENTS land in the category, not which combinations the category allows.")
    lines.append("")
    lines.append("| category (e_m_j_b) | combinations ours | combinations PR #31 | same set |")
    lines.append("|---|---:|---:|:---:|")
    for r in rows:
        lines.append(f"| `{r['category']}` | {r['n_ours']} | {r['n_pr31']} | "
                     f"{'yes' if r['equal'] else '**NO**'} |")
    lines.append("")

    with open(args.out_md, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"combinations: ours={result['n_combinations_ours']} pr31={result['n_combinations_pr31']} "
          f"identical_sets={result['combination_pattern_sets_identical']}")
    print(f"categories: {len(all_cats)}; differing combination sets: {len(diffs)}")
    print(f"sum of per-category allowed combinations: ours={total_o} pr31={total_p}")
    print(f"wrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
