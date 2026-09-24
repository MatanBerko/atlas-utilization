"""
Background-model task, Part 2: per-category, per-family order selection.

ALGORITHM (documented explicitly, since the task's own instructions leave
one ambiguity -- what to do when the F-test-selected order fails the
GOF requirement):

1. Fit EVERY order in the family's declared range (cheap: <= 7 orders,
   each a multi-start Poisson NLL fit).
2. F-TEST SELECTION: starting at the lowest order, walk upward; at each
   step compute the F-test p-value comparing order k to order k+1
   (2*(NLL_k - NLL_{k+1}) vs. chi2 with delta-ndf dof). Keep climbing
   WHILE p < 0.05 (the increase is significant); stop at the first
   non-significant step. The "F-test order" is the last order that WAS
   a significant improvement over its predecessor (the lowest order if
   even the first step up is not significant).
3. GOF CHECK: evaluate the binned chi2 GOF p-value (bins with expected
   content >= 5) at the F-test order. If p > 0.01, that is the family's
   FINAL selected order.
4. GOF-DRIVEN OVERRIDE (this project's own documented resolution of the
   task's ambiguity): if the F-test order fails GOF, search UPWARD
   (orders above the F-test order, up to the family's max) for the
   first order whose OWN GOF p-value exceeds 0.01, using that order
   instead if found (the F-test says extra complexity isn't
   *significantly* better in the likelihood-ratio sense, but the
   absolute goodness-of-fit test says the F-test order still doesn't
   describe the data adequately -- in that conflict, GOF wins, since a
   background model that doesn't pass GOF at all is not usable
   regardless of what the F-test says about its neighbours).
5. If NO order in the family's entire range passes GOF, the family is
   DROPPED and reported as such (never silently discarded).
"""
from __future__ import annotations

import numpy as np

from studies.hgg_cms.background_model.families import FAMILIES, ORDER_RANGE
from studies.hgg_cms.background_model.fit_background import (
    fit_family_order, cross_check_second_optimizer, f_test_p_value, goodness_of_fit,
)

GOF_P_THRESHOLD = 0.01
FTEST_P_THRESHOLD = 0.05


def fit_all_orders(family_name: str, edges: np.ndarray, counts: np.ndarray, mask: np.ndarray) -> dict:
    fam = FAMILIES[family_name]
    orders = list(ORDER_RANGE[family_name])
    per_order = {}
    for order in orders:
        fit = fit_family_order(family_name, order, edges, counts, mask)
        gof = goodness_of_fit(family_name, order, edges, counts, mask, fit.params)
        per_order[order] = {
            "fit": fit, "gof": gof,
            "n_params": fam.n_params(order),
        }
    return per_order


def select_order(family_name: str, per_order: dict) -> dict:
    orders = sorted(per_order.keys())
    ftest_steps = []
    ftest_order = orders[0]
    for k, k1 in zip(orders[:-1], orders[1:]):
        fit_k = per_order[k]["fit"]
        fit_k1 = per_order[k1]["fit"]
        ndf_k = per_order[k]["fit"].mask.sum() - per_order[k]["n_params"]
        ndf_k1 = per_order[k1]["fit"].mask.sum() - per_order[k1]["n_params"]
        ftest = f_test_p_value(fit_k.nll, ndf_k, fit_k1.nll, ndf_k1)
        ftest_steps.append({"from_order": k, "to_order": k1, **ftest})
        if ftest["p_value"] < FTEST_P_THRESHOLD:
            ftest_order = k1
        else:
            break

    gof_at_ftest_order = per_order[ftest_order]["gof"]
    final_order = None
    override_used = False
    if gof_at_ftest_order["p_value"] > GOF_P_THRESHOLD:
        final_order = ftest_order
    else:
        for k in orders:
            if k <= ftest_order:
                continue
            if per_order[k]["gof"]["p_value"] > GOF_P_THRESHOLD:
                final_order = k
                override_used = True
                break

    dropped = final_order is None
    return {
        "family": family_name,
        "orders_tried": orders,
        "ftest_steps": ftest_steps,
        "ftest_selected_order": ftest_order,
        "gof_at_ftest_order": gof_at_ftest_order,
        "gof_override_used": override_used,
        "final_selected_order": final_order,
        "dropped_family_fails_gof_everywhere": dropped,
    }


def run_category_order_selection(edges: np.ndarray, counts: np.ndarray, mask: np.ndarray) -> dict:
    out = {}
    for family_name in FAMILIES:
        per_order = fit_all_orders(family_name, edges, counts, mask)
        selection = select_order(family_name, per_order)
        cross_check = None
        if selection["final_selected_order"] is not None:
            k = selection["final_selected_order"]
            cross_check = cross_check_second_optimizer(
                family_name, k, edges, counts, mask, per_order[k]["fit"]
            )
        out[family_name] = {
            "per_order": per_order, "selection": selection, "cross_check_final_order": cross_check,
        }
    return out
