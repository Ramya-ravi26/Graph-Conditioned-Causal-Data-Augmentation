import numpy as np
import pyvinecopulib as pv
from scipy.stats import kendalltau
import wandb

# Initialize logging
import os

# offline by default so the smoke test runs without credentials;
# set WANDB_MODE=online (and `wandb login`) to sync
wandb.init(project="graph-conditioned-augmentation", name="smoke-test", mode=os.environ.get("WANDB_MODE", "offline"))

# Step 1: generate synthetic data
SEED = 42
np.random.seed(SEED)
u = np.random.rand(1000, 2)

# Step 2: fit copula
cop = pv.Bicop(pv.BicopFamily.gaussian)
cop.fit(u)
# Step 3: sample from copula
samples = cop.simulate(1000)

# Step 4: compute dependence
tau_orig = kendalltau(u[:, 0], u[:, 1])[0]
tau_gen = kendalltau(samples[:, 0], samples[:, 1])[0]

print(f"Original tau: {tau_orig:.4f}")
print(f"Generated tau: {tau_gen:.4f}")

# Log to W&B
wandb.log({
    "tau_original": tau_orig,
    "tau_generated": tau_gen,
    "copula_family": "gaussian",
    "samples": 1000,
    "seed": SEED,
})
