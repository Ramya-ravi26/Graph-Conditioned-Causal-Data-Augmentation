"""T6c/T7: sweep key hyperparameters (thin wrapper around gcda.experiments.sweep).

Run: python scripts/sweep_hyperparameters.py [--wandb] [--config PATH]

W&B logging defaults to offline mode (no credentials needed, writes under
wandb/); set WANDB_MODE=online and log in beforehand to sync for real.
"""

import argparse
from pathlib import Path

from gcda.experiments.sweep import DEFAULT_CONFIG_PATH, main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wandb", action="store_true", help="log each run to Weights & Biases (offline by default)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="sweep config YAML")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    kwargs = {"output_dir": args.output_dir} if args.output_dir else {}
    main(config_path=args.config, use_wandb=args.wandb, **kwargs)
