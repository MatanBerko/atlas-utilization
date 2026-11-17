README_plots.txt  --  pictures of every histogram of the CMS MC delivery (17 Nov 2026)
=====================================================================================

WHAT IS HERE
  pngs/<histogram name>.png   one picture per histogram of the summed MC file, 331 in all
                              (1600 x 1200 pixels, 150 dpi); 313 with data,
                              18 MC-only (four-lepton final states not in the data file)
  CMS_Run2016GH_MC-summedSM-71samples_vs_data_16p393invfb_plots_2026-11-17.pdf
                              the same 331 pictures, one per page, after 7 contents pages
                              (each picture's page number is in the contents and on the picture)
  SHA256SUMS.txt              checksums of every file in this folder

WHAT ONE PICTURE SHOWS
  Top: the simulation (MC), 71 samples stacked by process group (colours below), with its statistical
  uncertainty as a hatched band around the MC total (black line); the CMS data as black points with
  Poisson (68 %) error bars. Logarithmic vertical axis, events per 10 GeV bin.
  Bottom (only when there is data): data divided by MC per bin, with the data errors, the MC
  uncertainty band around 1 and a line at 1; range 0-2.5 (points above 2.5 are shown as triangles at
  the top edge).
  Text: the histogram name, the final state in words, "CMS Open Data 2016 (Run G+H), 16.4 fb-1,
  sqrt(s) = 13 TeV", the integrals of data and MC from the common start and their ratio, and
  "MC missing: QCD multijet, photon processes".
  These are not official CMS results; no CMS label is used.

IMPORTANT: QCD multijet and photon processes are NOT in the MC. Where they matter (single lepton +
  jets above all) the data lie above the MC.

COLOURS (fixed for all pictures; stacking order bottom to top as listed)
  #2a78d6  Drell-Yan  (records 35631, 35669)
  #eb6834  W+jets  (records 69715, 69717, 69719)
  #1baf7a  ttbar  (records 67801, 67993, 67841)
  #eda100  single top  (records 64635, 64659, 64759, 64839, 64895)
  #e87ba4  dibosons  (records 72658, 72676, 72738, 72740, 72742, 72752, 75567, 75573, 75589)
  #008300  tribosons, ttbar+X (ttW, ttZ, ttH), four top, rare top (tZq, tWll)  (records 72701, 72711, 72761, 75600, 67645, 67691, 68045, 68073, 68083, 68185, 68187, 68206, 68325, 64873)
  #6250d6  Z->nunu  (records 74894, 74896, 74898, 74900, 74902, 74904, 74906)
  #e34948  Higgs  (records 37432, 37446, 37474, 37604, 37616, 37728, 40062, 40095, 41873, 41877, 41914, 68571, 68591, 68601, 68731, 68741, 68847, 70301, 70383, 70451, 70453, 71145, 71227, 71295, 71297, 74292, 74682, 74684)
  A group whose net weight in a bin is negative (negative generator weights) is drawn as zero in that
  bin; the black MC total line, the band and all numbers use the true total.

CROPPING RULE (horizontal range)
  From the common start = the later of the data's and the MC's first filled bin (column
  common_start_gev of the start-mass CSV; the rule of the MC README) to the last bin filled in data
  or MC. MC-only histograms start at the MC's first filled bin.

INTEGRALS ON THE PICTURE
  data = sum of the data bins from the common start to 10,000 GeV; MC = the same for the summed MC
  file; data/MC = their ratio. These equal the columns data_from_common_start and
  mc_from_common_start of the CSV. MC-only: the MC sum from its first filled bin.

SOURCE FILES (read only)
  data (25 Oct, uncropped):
    CMS_Run2016GH_DoubleMuon-SingleMuon-DoubleEG-MuonEG-SingleElectron_16p393invfb_prod2026-10-25_data_bumpnet_uncropped.root
    sha256 fc9545191df7ceeb6fc7d00c80d7968012b803fd63bdf5d5e8a0677b249bdbaf
  MC summed (14 Nov):
    CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root
    sha256 91beacdf4056e85804a9cb168195faf41dad9a712c4f2e1ab5e77d6bec26bd03
  start-mass CSV:
    CMS_Run2016GH_MC-summedSM-71samples_16p393invfb_build2026-11-14_mc.root.start_masses.csv
    sha256 1d217bd0174ce1ad8efcf63118c12c58a257b01fa281675e629b17f891062614
  plus the 71 per-sample MC files (per_sample/ of the MC delivery) for the stacking; the stacked total
  equals the summed file in every histogram (largest relative difference
  1.1e-15).

MADE BY
  studies/mc_expansion_20261103/delivery/plots_20261117/make_histogram_plots.py
  (github.com/MatanBerko/atlas-utilization, branch feature/mc-expansion-20261103), 17 Nov 2026.
