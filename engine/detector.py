"""
DrishtiAI -- DR Detection Engine (Dual-Model Architecture)
Primary: EfficientNet-B3 (PyTorch, 43MB, 5-class, 300x300)
  Supports both timm (Kaggle-trained) and torchvision (RishiSwethan) formats.
Fallback: Tanwar-12's CNN (TensorFlow, 0.4MB, regression, 64x64)
"""
import numpy as np
import os
import json
from config import DR_MODEL_PATH, DR_STAGES, IMG_SIZE

# Model cache
_pytorch_model = None
_tf_model = None
_active_model_type = None  # 'pytorch' or 'tensorflow'

# Paths
PYTORCH_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(DR_MODEL_PATH)), 'best_model_final.pt')
PYTORCH_HP_PATH = os.path.join(os.path.dirname(DR_MODEL_PATH), 'vessel_model', 'best_hp.json')

# EfficientNet-B3 input size
EFFNET_INPUT_SIZE = 300


def _load_pytorch_model():
    """Load EfficientNet-B3 model. Supports both timm and torchvision formats."""
    global _pytorch_model, _active_model_type

    if _pytorch_model is not None:
        _active_model_type = 'pytorch'
        return _pytorch_model

    model_path = PYTORCH_MODEL_PATH
    if not os.path.exists(model_path):
        alt_path = os.path.join(os.path.dirname(DR_MODEL_PATH), 'dr_pipeline', 'best_model.pt')
        if os.path.exists(alt_path):
            model_path = alt_path
        else:
            print("[WARNING] EfficientNet-B3 model not found at {}".format(PYTORCH_MODEL_PATH))
            return None

    try:
        import torch

        print("[MODEL] Loading EfficientNet-B3 from {}...".format(model_path))
        state_dict = torch.load(model_path, map_location='cpu', weights_only=False)

        # Handle checkpoint wrapper (from train_model.py)
        if isinstance(state_dict, dict) and 'model_state_dict' in state_dict:
            state_dict = state_dict['model_state_dict']

        # Remove 'model.' prefix if present (RishiSwethan format)
        clean_sd = {}
        for key, value in state_dict.items():
            clean_sd[key[6:] if key.startswith('model.') else key] = value

        # Detect format:
        # 1. DrishtiAI DRGradingModel (features + fusion + ordinal_head + referable_head)
        # 2. timm (conv_stem.weight)
        # 3. torchvision (features.0.0.weight with classifier)
        is_dr_pipeline = 'ordinal_head.weight' in clean_sd or 'fusion.0.weight' in clean_sd
        is_timm = 'conv_stem.weight' in clean_sd

        if is_dr_pipeline:
            from engine.pipeline.grading import DRGradingModel
            model = DRGradingModel(pretrained=False)
            model.load_state_dict(clean_sd, strict=True)
            model._model_format = 'dr_pipeline_ordinal'
            print("[OK] DRGradingModel loaded (DR Pipeline ordinal format, 5-class, 300x300)")
        elif is_timm:
            # New Kaggle-trained model (timm format)
            try:
                import timm
            except ImportError:
                print("[WARNING] timm not installed, trying pip install...")
                os.system('pip install -q timm')
                import timm
            model = timm.create_model('efficientnet_b3', pretrained=False, num_classes=5)
            model.load_state_dict(clean_sd, strict=True)
            model._model_format = 'timm'
            print("[OK] EfficientNet-B3 loaded (timm/Kaggle format, 5-class, 300x300)")
        else:
            # Old RishiSwethan model (torchvision format)
            import torchvision.models as models
            model = models.efficientnet_b3(weights=None)
            num_features = model.classifier[1].in_features  # 1536

            # Auto-detect classifier architecture
            has_enhanced_head = any('classifier.3' in k for k in clean_sd)
            if has_enhanced_head:
                model.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.4),
                    torch.nn.Linear(num_features, 512),
                    torch.nn.ReLU(inplace=True),
                    torch.nn.BatchNorm1d(512),
                    torch.nn.Dropout(p=0.3),
                    torch.nn.Linear(512, 5),
                )
                print("[MODEL] Detected enhanced classifier head")
            else:
                model.classifier = torch.nn.Linear(num_features, 5)

            model.load_state_dict(clean_sd, strict=True)
            model._model_format = 'torchvision'
            print("[OK] EfficientNet-B3 loaded (torchvision format, 5-class, 300x300)")

        model.eval()
        _pytorch_model = model
        _active_model_type = 'pytorch'
        return model

    except Exception as e:
        print("[WARNING] Failed to load EfficientNet-B3: {}".format(e))
        print("[FALLBACK] Will try Tanwar-12 TF model...")
        return None


def _load_tf_model():
    """Load Tanwar-12's TensorFlow CNN model (fallback)."""
    global _tf_model, _active_model_type

    if _tf_model is not None:
        _active_model_type = 'tensorflow'
        return _tf_model

    if not os.path.exists(DR_MODEL_PATH):
        print("[WARNING] TF Model not found at {}".format(DR_MODEL_PATH))
        return None

    try:
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

        print("[MODEL] Loading Tanwar-12 CNN from {}...".format(DR_MODEL_PATH))
        _tf_model = tf.keras.models.load_model(DR_MODEL_PATH, compile=False)
        _active_model_type = 'tensorflow'
        print("[OK] TF Model loaded! Input shape: {}".format(_tf_model.input_shape))
        return _tf_model
    except Exception as e:
        print("[ERROR] Failed to load TF model: {}".format(e))
        return None


def _load_model():
    """Load the best available model. Tries EfficientNet-B3 first, then TF CNN."""
    # Try PyTorch EfficientNet-B3 first (better accuracy)
    model = _load_pytorch_model()
    if model is not None:
        return model

    # Fallback to TensorFlow CNN
    model = _load_tf_model()
    if model is not None:
        return model

    print("[ERROR] No model available!")
    return None


def _preprocess_for_effnet(image):
    """
    Preprocess image for EfficientNet-B3 inference.
    Input: numpy array of any shape (H, W, 3), uint8 or float
    Output: (300, 300, 3) normalized numpy array
    """
    import cv2

    # Ensure uint8
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = image.astype(np.uint8)

    # Resize to 300x300 for EfficientNet-B3
    resized = cv2.resize(image, (EFFNET_INPUT_SIZE, EFFNET_INPUT_SIZE))

    # Normalize to [0, 1]
    normalized = resized.astype(np.float32) / 255.0

    return normalized


def predict(preprocessed_image):
    """
    Run DR classification on a preprocessed image.

    Args:
        preprocessed_image: numpy array, normalized to [0, 1]

    Returns:
        dict with stage, stage_name, confidence, all_probabilities, etc.
    """
    model = _load_model()

    if model is None:
        return _mock_prediction()

    if _active_model_type == 'pytorch':
        return _predict_pytorch(preprocessed_image, model)
    else:
        return _predict_tensorflow(preprocessed_image, model)


def _predict_pytorch(image, model):
    """Run prediction with EfficientNet-B3 PyTorch model."""
    import torch

    # Preprocess for EfficientNet
    effnet_input = _preprocess_for_effnet(image)

    # Convert to PyTorch tensor: (H, W, C) -> (C, H, W)
    tensor = torch.from_numpy(effnet_input).permute(2, 0, 1).unsqueeze(0)

    # ImageNet normalization
    mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    tensor = (tensor - mean) / std

    # Inference
    with torch.no_grad():
        if getattr(model, '_model_format', None) == 'dr_pipeline_ordinal':
            from engine.pipeline.grading import ordinal_probs
            ord_logits, ref_logits = model(tensor)
            probs = ordinal_probs(ord_logits).cpu().numpy()[0]
        else:
            output = model(tensor)
            probs = torch.nn.functional.softmax(output, dim=1).cpu().numpy()[0]

    stage = int(np.argmax(probs))
    confidence = float(probs[stage] * 100)
    all_probs = {i: float(probs[i] * 100) for i in range(5)}

    stage_info = DR_STAGES.get(stage, DR_STAGES[0])

    return {
        "stage": stage,
        "stage_name": stage_info["name"],
        "confidence": round(confidence, 1),
        "all_probabilities": all_probs,
        "severity": stage_info["severity"],
        "color": stage_info["color"],
        "_model": "EfficientNet-B3 (DrishtiAI)",
    }


def _predict_tensorflow(image, model):
    """Run prediction with Tanwar-12's TF CNN model."""
    # Expand dims for batch
    input_batch = np.expand_dims(image, axis=0)

    predictions = model.predict(input_batch, verbose=0)

    if predictions.shape[-1] == 1:
        # Regression output
        stage = int(np.clip(np.round(predictions[0][0]), 0, 4))
        confidence = max(60.0, 95.0 - abs(predictions[0][0] - stage) * 30)
        all_probs = {i: (90.0 if i == stage else 2.5) for i in range(5)}
    else:
        # Classification output
        probs = predictions[0]
        if np.min(probs) < 0 or np.sum(probs) > 1.5:
            exp_probs = np.exp(probs - np.max(probs))
            probs = exp_probs / exp_probs.sum()
        stage = int(np.argmax(probs))
        confidence = float(probs[stage] * 100)
        all_probs = {i: float(probs[i] * 100) for i in range(5)}

    stage_info = DR_STAGES.get(stage, DR_STAGES[0])

    return {
        "stage": stage,
        "stage_name": stage_info["name"],
        "confidence": round(confidence, 1),
        "all_probabilities": all_probs,
        "severity": stage_info["severity"],
        "color": stage_info["color"],
        "_model": "CNN (Tanwar-12)",
        "primary_failure": True,
        "fallback_used": True,
        "fallback_reason": "Primary EfficientNet-B3 unavailable; executed secondary TensorFlow CNN fallback.",
        "fallback_model_version": "Tanwar-12-v1.0",
        "calibration_version": "UNCHECKED_FALLBACK",
    }


def validate_model_output(prediction: dict | None) -> bool:
    """Validate that model output dictionary adheres to safety and structural contracts."""
    valid, _ = validate_model_output_detailed(prediction)
    return valid


def validate_model_output_detailed(prediction: dict | None) -> tuple[bool, str | None]:
    """
    Validate that model output dictionary adheres to safety and structural contracts.
    Returns (is_valid: bool, reason_code: str | None).
    Handles:
      - null, empty, or non-dict prediction
      - unexpected class or invalid class index (<0 or >4)
      - negative probability, probability > 100%
      - IEEE-754 non-finite values (NaN, +Inf, -Inf)
      - probability distribution not approximately summing to 1 (or 100)
      - invalid confidence (< 0 or > 100 or non-finite)
    """
    import math

    if not isinstance(prediction, dict) or not prediction:
        return False, "MODEL_OUTPUT_MISSING_OR_EMPTY"

    # Check model_available / primary_failure flags
    if prediction.get("model_available") is False or prediction.get("primary_failure") is True:
        if not prediction.get("fallback_used"):
            return False, "MODEL_FAILURE"

    if "stage" not in prediction or "confidence" not in prediction:
        return False, "MODEL_OUTPUT_MISSING_FIELDS"

    # Validate stage
    raw_stage = prediction.get("stage")
    try:
        if raw_stage is None or isinstance(raw_stage, (bool, list, dict)):
            return False, "INVALID_STAGE_FORMAT"
        stage = int(raw_stage)
        if stage not in (0, 1, 2, 3, 4):
            return False, "INVALID_STAGE_INDEX"
    except (ValueError, TypeError):
        return False, "INVALID_STAGE_FORMAT"

    # Validate confidence
    raw_conf = prediction.get("confidence")
    try:
        if raw_conf is None or isinstance(raw_conf, (bool, list, dict)):
            return False, "INVALID_CONFIDENCE_FORMAT"
        conf = float(raw_conf)
        if math.isnan(conf) or math.isinf(conf):
            return False, "NUMERICAL_INSTABILITY_DETECTED"
        if conf < 0.0 or conf > 100.0:
            return False, "CONFIDENCE_OUT_OF_BOUNDS"
    except (ValueError, TypeError):
        return False, "INVALID_CONFIDENCE_FORMAT"

    # Validate all_probabilities if present
    probs = prediction.get("all_probabilities")
    if probs is not None:
        if not isinstance(probs, dict):
            return False, "PROBABILITY_DISTRIBUTION_MALFORMED"
        try:
            prob_vals = []
            for k, v in probs.items():
                pv = float(v)
                if math.isnan(pv) or math.isinf(pv):
                    return False, "NUMERICAL_INSTABILITY_DETECTED"
                if pv < 0.0:
                    return False, "NEGATIVE_PROBABILITY_DETECTED"
                prob_vals.append(pv)
            p_sum = sum(prob_vals)
            if p_sum > 2.0:
                # 0-100% scale
                if any(pv > 100.0 for pv in prob_vals):
                    return False, "PROBABILITY_EXCEEDS_100_PERCENT"
                if abs(p_sum - 100.0) > 10.0:
                    return False, "PROBABILITY_DISTRIBUTION_UNNORMALIZED"
            else:
                # 0-1.0 scale
                if any(pv > 1.0 for pv in prob_vals):
                    return False, "PROBABILITY_EXCEEDS_100_PERCENT"
                if abs(p_sum - 1.0) > 0.10:
                    return False, "PROBABILITY_DISTRIBUTION_UNNORMALIZED"
        except (ValueError, TypeError):
            return False, "PROBABILITY_DISTRIBUTION_MALFORMED"

    return True, None


def _mock_prediction():
    """Return a deterministic conservative baseline when neural model weights are absent."""
    stage = 0
    confidence = 50.0  # Conservative uncertainty score
    stage_info = DR_STAGES[stage]
    return {
        "stage": stage,
        "stage_name": stage_info["name"],
        "confidence": confidence,
        "all_probabilities": {
            0: 50.0,
            1: 20.0,
            2: 15.0,
            3: 10.0,
            4: 5.0,
        },
        "severity": stage_info["severity"],
        "color": stage_info["color"],
        "_model": "Deterministic Baseline (Offline)",
        "_deterministic_fallback": True,
        "model_available": False,
        "primary_failure": True,
        "fallback_used": True,
        "fallback_reason": "Neural model weights unavailable; deterministic safe baseline returned.",
        "fallback_model_version": "Safe-Baseline-v1.0",
        "calibration_version": "CONSERVATIVE_HEURISTIC",
        "status": "UNABLE_TO_CLASSIFY",
    }


def get_model_for_gradcam():
    """Return the loaded Keras model (for Grad-CAM). Falls back to TF model."""
    # Grad-CAM works with TF/Keras, so always return TF model for that
    return _load_tf_model()
