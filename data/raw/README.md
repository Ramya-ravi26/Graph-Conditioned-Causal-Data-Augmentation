# Raw datasets

`gcda/data/resources/sachs_continuous.csv` (moved there so it is installed as
package data) is the Sachs et al. (2005) protein-signaling flow cytometry
dataset: 11 continuous variables, 7,466 single-cell measurements, mirrored from
the `CausalDiscoveryToolbox` package:
https://raw.githubusercontent.com/FenTechSolutions/CausalDiscoveryToolbox/master/cdt/data/resources/cyto_full_data.csv

**The 7,466 rows pool all nine experimental conditions of the original study**
(sizes 853, 902, 911, 723, 810, 799, 848, 913, 707), i.e. one general
stimulation (CD3/CD28) plus eight interventions. They are therefore not i.i.d.
observational data. `load_sachs(observational_only=True)` returns the first
853 rows, the CD3/CD28 condition. **Verified**: the first 853 rows match an independent copy of the observational
(CD3/CD28) data row by row (853/853; `scripts/verify_sachs_subset.py`, run on the
Lichtenberg cluster, `outputs/experiments/hpc/sachs_validation.txt`). Additional
evidence that the file concatenates the nine conditions in this order
(`tests/test_datasets.py`): every condition boundary shows a much larger
distribution shift than offsets inside the blocks, and the blocks carry the
expected intervention signatures (e.g. under the MEK inhibitor U0126 the median
of `p44/42` (Erk) drops from about 15 to 2.7).

Citation: Sachs, K., Perez, O., Pe'er, D., Lauffenburger, D. A., & Nolan,
G. P. (2005). Causal protein-signaling networks derived from multiparameter
single-cell data. Science, 308(5721), 523-529.

The other datasets are not stored as files:
- UCI-style robustness dataset: `sklearn.datasets.load_diabetes` (the
  Efron et al., 2004 diabetes data);
- synthetic SCMs are generated on the fly (`gcda/data/datasets.py`);
- Asia, Insurance and Alarm are sampled from the CPTs bundled with pgmpy.
