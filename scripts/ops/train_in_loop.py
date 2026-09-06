"""
DrishtiAI — closed-loop DR pipeline training entry point.

Examples:
    python train_in_loop.py --data data/aptos
    python train_in_loop.py --data /kaggle/input/aptos2019-blindness-detection \
        --max-iters 5 --epochs-full 10
    python train_in_loop.py --data data/aptos --no-lesion-features   (fast mode)

Artifacts written to models/dr_pipeline/:
    best_model.pt      — best checkpoint (by sens+spec+kappa composite)
    calibration.json   — temperature + referable decision threshold
    loop_history.json  — per-iteration clinical metrics (accuracy trend proof)
    review_queue.csv   — most-uncertain cases for ophthalmologist-in-the-loop
    lesion_cache.npz   — cached Module-2 lesion features
"""

import argparse

from training.loop_trainer import LoopConfig, LoopTrainer


def main() -> None:
    ap = argparse.ArgumentParser(description="DrishtiAI in-loop trainer")
    ap.add_argument("--data", default="data/aptos", help="APTOS dir or class folders")
    ap.add_argument("--out", default="models/dr_pipeline")
    ap.add_argument("--max-iters", type=int, default=6)
    ap.add_argument("--epochs-head", type=int, default=4)
    ap.add_argument("--epochs-partial", type=int, default=6)
    ap.add_argument("--epochs-full", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--img-size", type=int, default=300)
    ap.add_argument("--target-sens", type=float, default=0.90)
    ap.add_argument("--target-spec", type=float, default=0.85)
    ap.add_argument("--min-spec-for-threshold", type=float, default=0.85,
                    help="specificity floor during threshold search")
    ap.add_argument("--no-lesion-features", action="store_true",
                    help="skip Module-2 late fusion (faster, less accurate)")
    args = ap.parse_args()

    cfg = LoopConfig(
        data_dir=args.data,
        out_dir=args.out,
        max_iterations=args.max_iters,
        epochs_head=args.epochs_head,
        epochs_partial=args.epochs_partial,
        epochs_full=args.epochs_full,
        batch_size=args.batch_size,
        img_size=args.img_size,
        target_sensitivity=args.target_sens,
        target_specificity=args.target_spec,
        use_lesion_features=not args.no_lesion_features,
    )
    LoopTrainer(cfg).run()


if __name__ == "__main__":
    main()
