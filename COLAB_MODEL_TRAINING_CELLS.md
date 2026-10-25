# Inzira AI — exact Colab replacement cells

Use these cells in `Inzira_AI_NISR_2026_FINAL.ipynb`.

Keep the Drive setup and the data-loading cell that ends with `All three datasets loaded successfully!`. Delete every cell below that data-loading cell, beginning with **Identifying Household Keys and Relevant Features**. Those later cells are exploratory, duplicated, or part of the one-epoch prototype. Then insert the following cells in order.

## Cell 1 — install and import model libraries

```python
!pip -q install "xgboost>=2.0" "catboost>=1.2" joblib

import json
import random
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf

from catboost import CatBoostClassifier
from xgboost import XGBClassifier

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras
from tensorflow.keras import layers

warnings.filterwarnings("ignore")

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
tf.keras.utils.set_random_seed(SEED)

# These were created in the Drive setup cell.
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("TensorFlow:", tf.__version__)
print("GPU devices:", tf.config.list_physical_devices("GPU"))
```

## Cell 2 — replace the old feature-engineering cell

```python
# LEAKAGE-SAFE HOUSEHOLD FEATURE ENGINEERING

def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def binary_from_codes(series, yes_codes=(1,), no_codes=(2,)):
    """Map documented survey codes to 1/0 and preserve missing/inapplicable values."""
    values = numeric(series)
    result = pd.Series(np.nan, index=series.index, dtype="float64")
    result.loc[values.isin(yes_codes)] = 1.0
    result.loc[values.isin(no_codes)] = 0.0
    return result


def household_any(series):
    """1 if anyone is yes, 0 if valid answers exist but none is yes, else NaN."""
    return series.max(skipna=True)


person_columns = [
    "hhid", "s1q1", "s1q3y", "s3q2", "s4aq1", "s4bq1",
    "s4bq8", "s4bq13a", "s4bq15", "s4bq23c",
    "s6aq4", "s6aq5", "s6aq6"
]

household_columns = [
    "hhid", "province", "district", "ur", "s5aq1", "s5aq2",
    "s5aq3", "s5aq7", "s5aq8", "s5cq1", "s5cq3", "s5cq8",
    "s5cq14", "s5cq20a", "s5cq25", "s5cq31",
    "s5dq1", "s5dq2", "s5dq3", "s5eq1", "s7aq4",
    "s7aq4a", "s7aq4b", "s7aq4c", "s7aq4d", "s7aq4e", "s7aq4f"
]

missing_person = sorted(set(person_columns) - set(person_df.columns))
missing_household = sorted(set(household_columns) - set(household_df.columns))
assert not missing_person, f"Missing person columns: {missing_person}"
assert not missing_household, f"Missing household columns: {missing_household}"

person = person_df[person_columns].copy()
person["age"] = numeric(person["s1q3y"])
person["female"] = (numeric(person["s1q1"]) == 2).astype(float)
person.loc[person["s1q1"].isna(), "female"] = np.nan

person["health_insurance"] = binary_from_codes(person["s3q2"])
person["ever_attended_school"] = binary_from_codes(person["s4aq1"])
person["vocational_training"] = binary_from_codes(
    person["s4bq1"], yes_codes=(1, 2), no_codes=(3,)
)
person["mobile_phone"] = binary_from_codes(person["s4bq8"])
person["computer_ownership"] = binary_from_codes(person["s4bq13a"])
person["recent_internet_use"] = binary_from_codes(person["s4bq15"])
person["mobile_financial_service"] = binary_from_codes(person["s4bq23c"])
person["agricultural_activity"] = binary_from_codes(person["s6aq4"])
person["wage_employment"] = binary_from_codes(person["s6aq5"])
person["nonfarm_business"] = binary_from_codes(person["s6aq6"])

person["is_child"] = (person["age"] < 18).astype(float)
person["is_working_age"] = person["age"].between(18, 64).astype(float)
person["is_elderly"] = (person["age"] >= 65).astype(float)
person.loc[person["age"].isna(), ["is_child", "is_working_age", "is_elderly"]] = np.nan

person_household = person.groupby("hhid").agg(
    household_members=("hhid", "size"),
    average_age=("age", "mean"),
    maximum_age=("age", "max"),
    female_share=("female", "mean"),
    children_count=("is_child", "sum"),
    working_age_count=("is_working_age", "sum"),
    elderly_count=("is_elderly", "sum"),
    insured_share=("health_insurance", "mean"),
    school_attendance_share=("ever_attended_school", "mean"),
    vocational_training=("vocational_training", household_any),
    mobile_phone=("mobile_phone", household_any),
    computer_ownership=("computer_ownership", household_any),
    recent_internet_use=("recent_internet_use", household_any),
    mobile_financial_service=("mobile_financial_service", household_any),
    agricultural_activity=("agricultural_activity", household_any),
    wage_employment=("wage_employment", household_any),
    nonfarm_business=("nonfarm_business", household_any),
).reset_index()

person_household["dependency_ratio"] = (
    person_household["children_count"] + person_household["elderly_count"]
) / person_household["working_age_count"].replace(0, np.nan)

household = household_df[household_columns].copy()
household = household.rename(columns={
    "s5aq1": "habitat_type",
    "s5aq2": "dwelling_type",
    "s5aq3": "sleeping_rooms",
    "s5aq7": "dwelling_owner",
    "s5aq8": "occupancy_status",
    "s5cq1": "main_water_source",
    "s5cq3": "drinking_water_source",
    "s5cq25": "toilet_type",
    "s5dq1": "wall_material",
    "s5dq2": "roof_material",
    "s5dq3": "floor_material",
})

household["sleeping_rooms"] = numeric(household["sleeping_rooms"])
household["insufficient_water"] = binary_from_codes(household["s5cq8"])
household["electricity_access"] = binary_from_codes(
    household["s5cq14"], yes_codes=(1, 2, 3), no_codes=(4,)
)
household["home_internet_access"] = binary_from_codes(household["s5cq20a"])
household["environmental_problem"] = binary_from_codes(household["s5cq31"])
household["recent_household_shock"] = binary_from_codes(household["s5eq1"])
household["livestock_ownership"] = binary_from_codes(household["s7aq4"])

livestock_columns = ["s7aq4a", "s7aq4b", "s7aq4c", "s7aq4d", "s7aq4e", "s7aq4f"]
for column in livestock_columns:
    household[column] = numeric(household[column])
household["livestock_count"] = household[livestock_columns].sum(axis=1, min_count=1)

household = household.drop(columns=[
    "s5cq8", "s5cq14", "s5cq20a", "s5cq31", "s5eq1", "s7aq4",
    *livestock_columns,
])

target = poverty_df[["hhid", "poverty"]].copy()
target["poverty"] = numeric(target["poverty"])

final_model_df = (
    household
    .merge(person_household, on="hhid", how="inner", validate="one_to_one")
    .merge(target, on="hhid", how="inner", validate="one_to_one")
)

final_model_df["crowding_ratio"] = (
    final_model_df["household_members"]
    / final_model_df["sleeping_rooms"].replace(0, np.nan)
)

# Direct consumption, expenditure, poverty and quintile variables are intentionally excluded.
assert final_model_df["hhid"].is_unique
assert final_model_df["poverty"].notna().all()
assert set(final_model_df["poverty"].astype(int).unique()) == {1, 2, 3}

print("Final shape:", final_model_df.shape)
print("Unique households:", final_model_df["hhid"].nunique())
print("Predictors:", final_model_df.shape[1] - 2)
display(final_model_df.head())
display(final_model_df["poverty"].value_counts().sort_index().to_frame("households"))
```

## Cell 3 — replace the old split and preprocessing cell

```python
# STRATIFIED TRAIN / VALIDATION / TEST SPLIT

X = final_model_df.drop(columns=["hhid", "poverty"])
y = final_model_df["poverty"].astype(int) - 1

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y,
    test_size=0.30,
    random_state=SEED,
    stratify=y,
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp,
    test_size=0.50,
    random_state=SEED,
    stratify=y_temp,
)

categorical_features = [
    "province", "district", "ur", "habitat_type", "dwelling_type",
    "dwelling_owner", "occupancy_status", "main_water_source",
    "drinking_water_source", "toilet_type", "wall_material",
    "roof_material", "floor_material",
]
numerical_features = [c for c in X.columns if c not in categorical_features]

preprocessor = ColumnTransformer([
    ("numeric", Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ]), numerical_features),
    ("categorical", Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ]), categorical_features),
])

X_train_processed = preprocessor.fit_transform(X_train).astype("float32")
X_val_processed = preprocessor.transform(X_val).astype("float32")
X_test_processed = preprocessor.transform(X_test).astype("float32")

classes = np.array([0, 1, 2])
weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
class_weight_dict = dict(zip(classes.tolist(), weights.tolist()))
train_sample_weight = np.array([class_weight_dict[int(label)] for label in y_train])

print("Train:", X_train_processed.shape)
print("Validation:", X_val_processed.shape)
print("Test:", X_test_processed.shape)
print("Class weights:", class_weight_dict)
print("Test set is now locked until final model selection.")
```

## Cell 4 — train all classical candidate models

```python
# TRAIN CLASSICAL CANDIDATE MODELS; VALIDATION SET ONLY

def metric_row(name, y_true, y_pred):
    recalls = recall_score(y_true, y_pred, labels=[0, 1, 2], average=None, zero_division=0)
    return {
        "model": name,
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_class_1": recalls[0],
        "recall_class_2": recalls[1],
        "recall_class_3": recalls[2],
    }


candidate_models = {
    "Dummy majority": DummyClassifier(strategy="most_frequent"),
    "Logistic regression": LogisticRegression(
        C=1.0, max_iter=3000, class_weight="balanced", random_state=SEED
    ),
    "Random forest": RandomForestClassifier(
        n_estimators=600, min_samples_leaf=2, max_features="sqrt",
        class_weight="balanced_subsample", n_jobs=-1, random_state=SEED
    ),
    "Extra trees": ExtraTreesClassifier(
        n_estimators=600, min_samples_leaf=2, max_features="sqrt",
        class_weight="balanced", n_jobs=-1, random_state=SEED
    ),
    "Histogram gradient boosting": HistGradientBoostingClassifier(
        learning_rate=0.06, max_iter=400, max_leaf_nodes=31,
        l2_regularization=1.0, early_stopping=True,
        validation_fraction=0.15, random_state=SEED
    ),
    "XGBoost": XGBClassifier(
        objective="multi:softprob", num_class=3, eval_metric="mlogloss",
        n_estimators=800, learning_rate=0.04, max_depth=5,
        min_child_weight=3, subsample=0.85, colsample_bytree=0.85,
        reg_alpha=0.1, reg_lambda=2.0, tree_method="hist",
        n_jobs=-1, random_state=SEED
    ),
    "CatBoost": CatBoostClassifier(
        loss_function="MultiClass", eval_metric="TotalF1:average=Macro",
        iterations=1000, learning_rate=0.04, depth=6,
        l2_leaf_reg=5.0, auto_class_weights="Balanced",
        random_seed=SEED, verbose=False, allow_writing_files=False
    ),
}

fitted_models = {}
validation_predictions = {}
validation_rows = []

for name, candidate in candidate_models.items():
    print(f"Training {name}...")

    if name in {"Histogram gradient boosting", "XGBoost"}:
        candidate.fit(X_train_processed, y_train, sample_weight=train_sample_weight)
    elif name == "CatBoost":
        candidate.fit(
            X_train_processed,
            y_train,
            eval_set=(X_val_processed, y_val),
            early_stopping_rounds=80,
            use_best_model=True,
        )
    else:
        candidate.fit(X_train_processed, y_train)

    prediction = candidate.predict(X_val_processed).astype(int).ravel()
    fitted_models[name] = candidate
    validation_predictions[name] = prediction
    validation_rows.append(metric_row(name, y_val, prediction))

classical_results = (
    pd.DataFrame(validation_rows)
    .sort_values(["macro_f1", "balanced_accuracy"], ascending=False)
    .reset_index(drop=True)
)

display(classical_results.style.format({
    "accuracy": "{:.4f}",
    "balanced_accuracy": "{:.4f}",
    "macro_f1": "{:.4f}",
    "recall_class_1": "{:.4f}",
    "recall_class_2": "{:.4f}",
    "recall_class_3": "{:.4f}",
}))
```

## Cell 5 — train the neural network properly

```python
# TRAIN REGULARIZED MLP WITH EARLY STOPPING

keras.backend.clear_session()

mlp = keras.Sequential([
    layers.Input(shape=(X_train_processed.shape[1],)),
    layers.Dense(128, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.30),
    layers.Dense(64, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.25),
    layers.Dense(32, activation="relu"),
    layers.Dropout(0.15),
    layers.Dense(3, activation="softmax"),
], name="Inzira_AI_MLP")

mlp.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

callbacks = [
    keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=15, restore_best_weights=True
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss", factor=0.5, patience=6, min_lr=1e-6
    ),
    keras.callbacks.ModelCheckpoint(
        MODEL_DIR / "best_mlp.keras", monitor="val_loss", save_best_only=True
    ),
    keras.callbacks.TensorBoard(log_dir=str(LOG_DIR / "final_mlp")),
]

history = mlp.fit(
    X_train_processed,
    y_train.to_numpy(),
    validation_data=(X_val_processed, y_val.to_numpy()),
    epochs=150,
    batch_size=128,
    class_weight=class_weight_dict,
    callbacks=callbacks,
    verbose=1,
)

mlp_val_probability = mlp.predict(X_val_processed, verbose=0)
mlp_val_prediction = mlp_val_probability.argmax(axis=1)

fitted_models["Neural network"] = mlp
validation_predictions["Neural network"] = mlp_val_prediction

all_results = pd.concat([
    classical_results,
    pd.DataFrame([metric_row("Neural network", y_val, mlp_val_prediction)]),
], ignore_index=True).sort_values(
    ["macro_f1", "balanced_accuracy"], ascending=False
).reset_index(drop=True)

display(all_results.style.format({
    "accuracy": "{:.4f}",
    "balanced_accuracy": "{:.4f}",
    "macro_f1": "{:.4f}",
    "recall_class_1": "{:.4f}",
    "recall_class_2": "{:.4f}",
    "recall_class_3": "{:.4f}",
}))

plt.figure(figsize=(10, 4))
plt.plot(history.history["loss"], label="Training loss")
plt.plot(history.history["val_loss"], label="Validation loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Inzira AI neural-network learning curves")
plt.legend()
plt.tight_layout()
plt.show()
```

## Cell 6 — select on validation, then evaluate the test set once

```python
# FINAL SELECTION AND ONE-TIME TEST EVALUATION

best_model_name = all_results.iloc[0]["model"]
best_model = fitted_models[best_model_name]

print("Selected using validation macro-F1:", best_model_name)

if best_model_name == "Neural network":
    test_probability = best_model.predict(X_test_processed, verbose=0)
    test_prediction = test_probability.argmax(axis=1)
else:
    test_prediction = best_model.predict(X_test_processed).astype(int).ravel()
    test_probability = (
        best_model.predict_proba(X_test_processed)
        if hasattr(best_model, "predict_proba") else None
    )

test_metrics = metric_row(best_model_name, y_test, test_prediction)
display(pd.DataFrame([test_metrics]).style.format({
    "accuracy": "{:.4f}",
    "balanced_accuracy": "{:.4f}",
    "macro_f1": "{:.4f}",
    "recall_class_1": "{:.4f}",
    "recall_class_2": "{:.4f}",
    "recall_class_3": "{:.4f}",
}))

print(classification_report(
    y_test,
    test_prediction,
    labels=[0, 1, 2],
    target_names=["Welfare category 1", "Welfare category 2", "Welfare category 3"],
    digits=4,
    zero_division=0,
))

matrix = confusion_matrix(y_test, test_prediction, labels=[0, 1, 2])
plt.figure(figsize=(6, 5))
sns.heatmap(
    matrix, annot=True, fmt="d", cmap="Blues",
    xticklabels=["Category 1", "Category 2", "Category 3"],
    yticklabels=["Category 1", "Category 2", "Category 3"],
)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title(f"Test confusion matrix — {best_model_name}")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "test_confusion_matrix.png", dpi=200, bbox_inches="tight")
plt.show()

all_results.to_csv(OUTPUT_DIR / "validation_model_comparison.csv", index=False)
pd.DataFrame([test_metrics]).to_csv(OUTPUT_DIR / "final_test_metrics.csv", index=False)

joblib.dump(preprocessor, MODEL_DIR / "preprocessor.joblib")

if best_model_name == "Neural network":
    best_model.save(MODEL_DIR / "final_model.keras")
else:
    joblib.dump(best_model, MODEL_DIR / "final_model.joblib")

metadata = {
    "selected_model": best_model_name,
    "selection_metric": "validation_macro_f1",
    "test_metrics": {k: (float(v) if k != "model" else v) for k, v in test_metrics.items()},
    "raw_features": X.columns.tolist(),
    "processed_feature_count": int(X_train_processed.shape[1]),
    "random_seed": SEED,
}

with open(MODEL_DIR / "model_metadata.json", "w", encoding="utf-8") as file:
    json.dump(metadata, file, indent=2)

print("Saved models to:", MODEL_DIR)
print("Saved results to:", OUTPUT_DIR)
```

## Stop after Cell 6

Do not tune anything against `y_test`. Copy the validation comparison table and final test table before continuing to explainability and the UI.
