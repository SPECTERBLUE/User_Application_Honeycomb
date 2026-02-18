from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, root_mean_squared_error, r2_score


def train_random_forest(
    X,
    y,
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Trains Random Forest for both classification & regression
    """

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Detect problem type
    if y.nunique() <= 10 and y.dtype != "float64":
        model = RandomForestClassifier(random_state=random_state)
        problem_type = "classification"
    else:
        model = RandomForestRegressor(random_state=random_state)
        problem_type = "regression"

    # Train
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)

    if problem_type == "classification":
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred)
        }
    else:
        metrics = {
            "rmse": root_mean_squared_error(y_test, y_pred),
            "r2_score": r2_score(y_test, y_pred)
        }

    return model, metrics
