"""Local High-Throughput ML Pipeline Tester (Multi-Core Parallelism).

Validates the distributed ML training architecture locally with an 8-point assertion suite:
1. Dataset shapes and binary label validity assertions.
2. StandardScaler zero-mean and unit-variance normalization assertions.
3. Stratified train/test split size and distribution assertions.
4. Multi-core GridSearchCV training and best estimator convergence assertions.
5. Metric boundary and performance assertions (0.0 <= auc <= 1.0, 0.0 <= acc <= 1.0, auc >= 0.70).
6. Model artifact serialization, file creation on disk, and size > 0 assertions.
7. Model deserialization and round-trip inference verification assertions.
8. Local PyTorch 16->64->2 deep learning architecture forward pass and backward step verification assertions.
"""
import os
import sys
import time
import pickle
from pathlib import Path
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

OUTPUT_DIR = Path(__file__).resolve().parent / "local_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_synthetic_data(num_samples: int = 50000, num_features: int = 16, seed: int = 2026):
    """Generates synthetic tabular dataset with feature-correlated signal for predictive learning."""
    print(f"Generating synthetic dataset: {num_samples:,} rows x {num_features} features...")
    rng = np.random.default_rng(seed)
    
    # Generate continuous features centered around 0
    X = rng.uniform(-50.0, 50.0, size=(num_samples, num_features))
    
    # Feature-correlated signal (ensures genuine learning signal with AUC >= 0.70)
    # Target is correlated with linear combination of salient features (X0, X1, X2)
    logits = (X[:, 0] * 0.35 + X[:, 1] * 0.25 - X[:, 2] * 0.20) / 10.0
    probs = 1.0 / (1.0 + np.exp(-logits))
    y = (rng.uniform(0.0, 1.0, size=num_samples) < probs).astype(np.float32)
    
    return X, y

def verify_pytorch_architecture():
    """Assertion 8: Validates the 16->64->2 deep learning architecture locally."""
    import torch
    import torch.nn as nn
    import torch.optim as optim

    # Sovereign Deep Learning Architecture: 16 -> 64 (BatchNorm, ReLU) -> 2
    model = nn.Sequential(
        nn.Linear(16, 64),
        nn.BatchNorm1d(64),
        nn.ReLU(),
        nn.Linear(64, 2)
    )
    model.train()

    # Forward pass verification
    x_test = torch.randn(32, 16)
    out = model(x_test)
    assert out.shape == (32, 2), f"PyTorch forward pass shape mismatch: expected (32, 2), got {out.shape}"

    # Optimization & backward step verification
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    target = torch.randint(0, 2, (32,))
    loss = criterion(out, target)
    assert not torch.isnan(loss) and loss.item() > 0.0, f"Invalid PyTorch loss value: {loss.item()}"

    optimizer.zero_grad()
    loss.backward()
    assert model[0].weight.grad is not None, "PyTorch backward pass failed to calculate gradients"
    assert not torch.isnan(model[0].weight.grad).any(), "PyTorch gradient contains NaN values"
    optimizer.step()

    print("  [PASS] Assertion 8: Local PyTorch 16->64->2 forward pass & backward step verified.")
    return True

def main():
    print("=" * 65)
    print("AI-BS LOCAL HIGH-THROUGHPUT ML TRAINING PIPELINE (RYZEN 9 9950X)")
    print("=" * 65)

    num_samples = int(os.getenv("NUM_SAMPLES", "50000"))
    num_features = 16

    start_data_t = time.time()
    X, y = generate_synthetic_data(num_samples=num_samples, num_features=num_features)
    print(f"Data generation complete in {time.time() - start_data_t:.3f}s")

    # 1. Dataset shapes and binary label validity assertions
    assert X.shape == (num_samples, num_features), f"Invalid feature matrix shape: expected ({num_samples}, {num_features}), got {X.shape}"
    assert y.shape == (num_samples,), f"Invalid target vector shape: expected ({num_samples},), got {y.shape}"
    unique_labels = set(np.unique(y))
    assert unique_labels == {0.0, 1.0}, f"Synthetic data must contain binary classes {0.0, 1.0}, got {unique_labels}"
    print(f"  [PASS] Assertion 1: Dataset shapes ({X.shape}) and binary label validity verified.")

    # 2. StandardScaler zero-mean and unit-variance normalization assertions
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    means = X_scaled.mean(axis=0)
    stds = X_scaled.std(axis=0)
    assert np.allclose(means, 0.0, atol=1e-1), f"StandardScaler mean is not zero: max deviation {np.max(np.abs(means))}"
    assert np.allclose(stds, 1.0, atol=1e-1), f"StandardScaler std is not unit: max deviation {np.max(np.abs(stds - 1.0))}"
    print("  [PASS] Assertion 2: StandardScaler zero-mean and unit-variance normalization verified.")

    # 3. Stratified train/test split size and distribution assertions
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=2026, stratify=y
    )
    expected_train_len = int(num_samples * 0.8)
    expected_test_len = int(num_samples * 0.2)
    assert len(X_train) == expected_train_len, f"Train split size mismatch: expected {expected_train_len}, got {len(X_train)}"
    assert len(X_test) == expected_test_len, f"Test split size mismatch: expected {expected_test_len}, got {len(X_test)}"
    assert abs(y_train.mean() - y_test.mean()) < 0.02, "Train/test stratified class distribution disparity exceeds tolerance"
    print(f"  [PASS] Assertion 3: Stratified split sizes verified ({len(X_train):,} train, {len(X_test):,} test).")

    # 4. Multi-core GridSearchCV training and best estimator convergence assertions
    param_grid = {
        'n_estimators': [15, 30],
        'max_depth': [5, 8]
    }
    rf = RandomForestClassifier(random_state=2026)
    cv = GridSearchCV(
        estimator=rf,
        param_grid=param_grid,
        cv=3,
        scoring='roc_auc',
        n_jobs=-1,
        verbose=0
    )

    print("\nBeginning multi-core cross-validation training...")
    start_train_t = time.time()
    cv.fit(X_train, y_train)
    train_duration = time.time() - start_train_t
    print(f"Training completed in {train_duration:.2f}s")
    print(f"Best Hyperparameters: {cv.best_params_}")

    assert cv.best_estimator_ is not None, "GridSearchCV failed to converge on a best estimator"
    assert "n_estimators" in cv.best_params_ and "max_depth" in cv.best_params_, "GridSearchCV missing expected best parameters"
    print("  [PASS] Assertion 4: Multi-core GridSearchCV training and best estimator convergence verified.")

    # 5. Metric boundary and performance assertions
    best_model = cv.best_estimator_
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)

    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)

    assert 0.0 <= auc <= 1.0, f"AUC metric out of [0.0, 1.0] bounds: {auc}"
    assert 0.0 <= acc <= 1.0, f"Accuracy metric out of [0.0, 1.0] bounds: {acc}"
    assert auc >= 0.70, f"AUC metric ({auc:.4f}) did not achieve genuine predictive threshold (>= 0.70)"
    assert acc >= 0.50, f"Accuracy metric ({acc:.4f}) did not exceed random chance (>= 0.50)"
    print(f"  [PASS] Assertion 5: Metric bounds & performance verified: AUC={auc:.4f} (>= 0.70), Accuracy={acc * 100:.2f}%")

    # 6. Model artifact serialization, file creation on disk, and size > 0 assertions
    export_path = OUTPUT_DIR / f"rf_model_{int(time.time())}.pkl"
    with open(export_path, "wb") as f:
        pickle.dump({"model": best_model, "scaler": scaler, "metrics": {"auc": auc, "acc": acc}}, f)

    assert export_path.exists(), f"Model artifact was not written to disk at {export_path}"
    assert export_path.stat().st_size > 0, f"Model artifact file {export_path} has 0 bytes"
    print(f"  [PASS] Assertion 6: Model artifact serialized to disk ({export_path.stat().st_size:,} bytes).")

    # 7. Model deserialization and round-trip inference verification assertions
    with open(export_path, "rb") as f:
        loaded_artifact = pickle.load(f)

    assert "model" in loaded_artifact and "scaler" in loaded_artifact and "metrics" in loaded_artifact, "Deserialized artifact schema invalid"
    assert loaded_artifact["metrics"]["auc"] == auc, "Deserialized AUC metric mismatch"

    sample_slice = X_test[:10]
    test_infer = loaded_artifact["model"].predict(sample_slice)
    test_infer_proba = loaded_artifact["model"].predict_proba(sample_slice)
    assert len(test_infer) == 10, f"Deserialized model prediction count mismatch: expected 10, got {len(test_infer)}"
    assert test_infer_proba.shape == (10, 2), f"Deserialized model proba shape mismatch: {test_infer_proba.shape}"
    assert np.array_equal(test_infer, y_pred[:10]), "Deserialized model predictions differ from original estimator"
    print("  [PASS] Assertion 7: Model deserialization and round-trip inference verified.")

    # 8. Local PyTorch 16->64->2 deep learning architecture forward pass and backward step
    verify_pytorch_architecture()

    print("\n" + "=" * 65)
    print("ALL 8 ML PIPELINE TEST ASSERTIONS PASSED (EXIT CODE 0)")
    print("=" * 65)

if __name__ == "__main__":
    main()


