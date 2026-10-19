"""Run the other #35-changed functions the CMS code uses on fixed random inputs; print a hash of every output."""
import hashlib, logging, sys
sys.path.insert(0, sys.argv[1])
import numpy as np, awkward as ak
from services.pipelines.post_processing_pipeline import _apply_z_peak_cut, _find_rightmost_highest_peak, _split_by_first_empty_bin
from services.calculations.im_calculator import IMCalculator
from services.calculations import physics_calcs
from services.pipelines.im_pipeline import _calculate_combination_invariant_mass
L = logging.getLogger("x"); h = hashlib.sha256()
def mark(tag):
    global h
    print(tag, h.hexdigest()[:16]); h = hashlib.sha256()
rng = np.random.default_rng(20261019)
for i in range(300):
    arr = np.concatenate([rng.exponential(150, rng.integers(0, 3000)), rng.uniform(2000, 6000, rng.integers(0, 20))]).astype(np.float32)
    sig = ["x_FS_0e_2m_1j_0b_IM_2m", "x_FS_1e_1m_0j_0b_IM_1e1m", "x_FS_2e_0m_2j_1b_IM_2e1j"][i % 3]
    a = _apply_z_peak_cut(arr, sig, 110.0, L); h.update(a.tobytes())
    p = _find_rightmost_highest_peak(a, 10.0, L); h.update(repr(p).encode())
    f = a if p is None else a[a >= p]
    m, o = _split_by_first_empty_bin(f, 10.0, L); h.update(m.tobytes()); h.update(o.tobytes()); h.update(str([x.dtype for x in (m, o) if len(x)]).encode())  # dtype of EMPTY arrays ignored: never written
mark("postproc")
def objs(n, k):
    c = rng.integers(0, k, n)
    tot = int(c.sum())
    rec = ak.zip({"pt": rng.uniform(10e3, 200e3, tot), "eta": rng.uniform(-2.4, 2.4, tot), "phi": rng.uniform(-3.1, 3.1, tot), "mass": np.zeros(tot)})
    return ak.unflatten(rec, c)
ev = ak.zip({"Electrons": objs(4000, 3), "Muons": objs(4000, 3), "Jets": objs(4000, 5), "BJets": objs(4000, 2)}, depth_limit=1)
calc = IMCalculator(events=ev, min_events_per_fs=1, min_k=1, max_k=4, min_n=2, max_n=4)
h.update(str(ak.to_list(physics_calcs.count_particles(ev) if hasattr(physics_calcs, "count_particles") else ak.num(ev))[:50]).encode())
mark("count_particles")
for label, fs in physics_calcs.group_by_final_state(ev):
    h.update(label.encode()); h.update(str(len(fs)).encode())
mark("group_by_final_state")
for combo in [{"Muons": 2}, {"Electrons": 1, "Muons": 1}, {"Jets": 2}, {"Electrons": 1, "Jets": 2, "BJets": 1}]:
    r = _calculate_combination_invariant_mass(ev, combo, {"field_to_slice_by": "pt"}, calc, L, "fs")
    h.update(np.asarray(ak.to_numpy(r[0]) if r[0] is not None else []).tobytes()); h.update(repr(r[-1]).encode())
    fl = physics_calcs.filter_events_by_particle_counts(ev, combo, is_exact_count=True)
    h.update(str(len(fl)).encode())
mark("im+filter")
