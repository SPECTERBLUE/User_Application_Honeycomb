from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight

def train_xgboost(X, y, test_size=0.2, random_state=42):

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    sample_weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train
    )

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        n_estimators=400,
        max_depth=6,
        learning_rate=0.08,
        random_state=random_state
    )

    model.fit(X_train, y_train, sample_weight=sample_weights)

    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True
        )
    }

    return model, metrics