# Training Lifecycle & Orchestration

## 1. Asynchronous Job State Machine
Training jobs transition through a strictly governed lifecycle:
`QUEUED` -> `RUNNING` -> `COMPLETED` | `FAILED` | `CANCELLED`

Jobs are tracked in the `training_runs` database table with configuration parameters, duration, loss curves, and artifact locations.

## 2. Curriculum Training & Hard-Example Mining
DrishtiAI employs closed-loop progressive unfreezing:
1. **Head Tuning**: Linear evaluation with frozen backbone.
2. **Partial Unfreezing**: Higher convolutional blocks unfrozen with reduced learning rate.
3. **Full Optimization**: End-to-end backpropagation with ordinal loss and focal weighting.
4. **Hard-Example Mining**: High-loss and borderline samples identified and upweighted dynamically.

## 3. Checkpointing & Post-Training Calibration
Every run exports:
- `best_model.pt` / `model.onnx`
- `calibration.json`: Temperature scaling parameters ensuring predicted probabilities reflect true empirical clinical risk.
