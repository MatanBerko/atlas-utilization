#!/usr/bin/env python
"""
Full run 25 Oct 2026: the data completeness check for the FIVE delivered
datasets (matched5).

ADDED because studies/cms_datasets/electron_vB/check_production_complete.py
loops over DELIVERY_VETO_ORDER_4 only, so it would never look at
SingleElectron. This runs that script's own main(), unchanged, with its
dataset list set to DELIVERY_VETO_ORDER_5. Same arguments, same report,
same exit code (non-zero if anything is missing or incomplete).

Usage:
    python studies/fullrun_20261025/check_production_complete_5.py \
        --runs-root <runs dir holding <Dataset>_index.json and <Dataset>/job_N/> --out <json>
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_5  # noqa: E402
from studies.cms_datasets.electron_vB import check_production_complete as cpc  # noqa: E402

if __name__ == "__main__":
    cpc.DELIVERY_VETO_ORDER_4 = list(DELIVERY_VETO_ORDER_5)
    cpc.main()
