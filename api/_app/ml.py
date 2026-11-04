"""Model loading + prediction. Never raises anything except ModelUnavailable."""
import logging
import pickle

from flask import current_app

log = logging.getLogger("healthpulse")
_cache = {}


class ModelUnavailable(Exception):
    pass


def _model_path(kind):
    cfg = current_app.config
    name = cfg["DIABETES_MODEL_FILE"] if kind == "diabetes" else cfg["HEART_MODEL_FILE"]
    # Resolved from the app's own location, NOT os.getcwd() (the cwd differs on Vercel).
    return cfg["MODEL_DIR"] / name


def load_model(kind):
    if kind in _cache:
        return _cache[kind]
    path = _model_path(kind)
    if not path.is_file():
        log.error("Model file missing: %s", path)
        raise ModelUnavailable(f"model file not found: {path.name}")
    try:
        with open(path, "rb") as fh:
            model = pickle.load(fh)
    except Exception as exc:  # noqa: BLE001 - version mismatch, missing sklearn, corrupt file ...
        log.exception("Could not load model %s", path)
        raise ModelUnavailable(f"could not load {path.name}: {exc}") from exc
    _cache[kind] = model
    return model


def predict(kind, feature_vector):
    """Return (prediction 0/1, probability of class 1 or None)."""
    model = load_model(kind)
    try:
        import numpy as np

        x = np.array([feature_vector], dtype=float)
        pred = int(model.predict(x)[0])
        prob = None
        if hasattr(model, "predict_proba"):
            classes = list(getattr(model, "classes_", [0, 1]))
            if 1 in classes:
                prob = float(model.predict_proba(x)[0][classes.index(1)])
        return pred, prob
    except Exception as exc:  # noqa: BLE001
        log.exception("Prediction failed")
        raise ModelUnavailable(f"prediction failed: {exc}") from exc
