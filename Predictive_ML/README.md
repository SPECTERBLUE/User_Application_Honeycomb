
```md
# 🧠 Predictive_ML Module

The **Predictive_ML** module provides end-to-end machine learning capabilities for predictive maintenance.

It supports:

- Training ML models
- Storing trained models in Redis
- Loading models for inference
- Running predictions
- Listing and deleting stored models
- User-defined model versioning
- Horizon-based future prediction (1, 6, 24 hours)

---

# 📦 Project Structure


Predictive_ML/
│
├── ml/
│ ├── trainers/
│ │ ├── random_forest.py
│ │ └── **init**.py
│ │
│ ├── model_store.py
│ ├── prediction.py
│ ├── train_service.py
│ └── **init**.py
│
├── fetch_assets_telemetry.py
├── telemetry_processor.py
├── training_dataset_csv_creation.py
├── predict_api.py


---

# 📂 Module Structure Explanation

## 📁 ml/

Core machine learning logic lives here.  
This folder contains all training, storage, and prediction-related components.

---

## 📁 ml/trainers/

Contains algorithm-specific training implementations.  
This structure allows easy extension to support multiple ML algorithms.

### 🔹 `random_forest.py`

Implements Random Forest model training using **scikit-learn**.

**Responsibilities:**

- Split dataset into train/test
- Train RandomForest model
- Support classification and regression
- Return trained model
- Return evaluation metrics:
  - Accuracy
  - Precision
  - Recall
  - etc.

**Extensible for:**

- Hyperparameter tuning
- GridSearch
- Additional ML algorithms

---

### 🔹 `__init__.py (trainers)`

- Makes the trainers directory a Python module  
- Enables clean imports

---

## 🔹 `model_store.py`

Responsible for model persistence in Redis.

**Responsibilities:**

- Serialize models using pickle
- Store model metadata as JSON
- Load models from Redis
- List stored models
- Delete models
- Maintain model registry set

### Redis Keys Used

```

ml:model:{model_name}
ml:model:meta:{model_name}
ml:model:list

````

---

## 🔹 `train_service.py`

Acts as the training orchestration layer.

**Responsibilities:**

- Load training dataset (CSV)
- Select algorithm (`random_forest`, etc.)
- Call appropriate trainer
- Collect evaluation metrics
- Prepare metadata
- Store model in Redis using `model_store`

This connects the API layer with ML logic.

---

## 🔹 `prediction.py`

Responsible for:

- Loading stored model
- Preprocessing input features
- Running inference
- Returning prediction results

Used internally by `predict_api`.

---

## 🔹 `__init__.py (ml)`

- Marks `ml` as a Python module  
- Enables clean imports

```python
from Predictive_ML.ml.train_service import TrainService
````

---

# 📊 Telemetry & Dataset Processing

These files handle data preparation before model training.

---

## 🔹 `fetch_assets_telemetry.py`

**Responsibilities:**

* Fetch raw telemetry data
* Retrieve telemetry for:

  * Entire asset
  * Specific thing within asset
* Act as data source connector

---

## 🔹 `telemetry_processor.py`

Processes raw telemetry data.

**Responsibilities:**

* Aggregate data using configurable time windows
* Handle missing windows
* Apply threshold-based labeling
* Convert raw telemetry into structured ML-ready dataset

---

## 🔹 `training_dataset_csv_creation.py`

**Responsibilities:**

* Convert processed & labeled data into CSV
* Save dataset under:

```
data/training_datasets/
```

* Return dataset path for training API

---

## 🔹 `predict_api.py`

Runs predictions using stored ML models.

**Responsibilities:**

* Fetch telemetry data for a given asset
* Aggregate using configured window length
* Handle missing windows
* Load trained model & metadata from Redis
* Run inference
* Return predictions for future horizon:

  * 1 hour
  * 6 hours
  * 24 hours

### Redis Keys Used

```
Window_length:{asset_id}
threshold_map:{asset_id}
ml:model:{model_name}
ml:model:meta:{model_name}
```

---

# 🔄 Overall Workflow

1. Fetch telemetry
2. Aggregate and label data
3. Generate training CSV
4. Train ML model
5. Store model in Redis
6. Load model for prediction
7. Predict future horizon values

---

# 🧩 Model Versioning

Model versioning is handled using a **user-defined unique model name**.

### During model training:

* Client must provide a `model_name`
* System checks Redis for duplicates
* If name exists → API returns **400 error**
* Existing models are **never overwritten**

This ensures safe and controlled model lifecycle management.

---

# 🌐 API Endpoints

Defined in:

```
api_downlink.py
```

| Method | Endpoint                                      | Description                                                   |
| ------ | --------------------------------------------- | ------------------------------------------------------------- |
| POST   | `/downlink/predictive_ML/assets/telemetry`    | Fetch, aggregate, label telemetry & generate training dataset |
| POST   | `/downlink/predictive_ML/things/telemetry`    | Fetch telemetry for specific thing                            |
| GET    | `/downlink/predictive_ML/datasets`            | List available training CSV datasets                          |
| POST   | `/downlink/predictive_ML/train`               | Train ML model & store in Redis                               |
| GET    | `/downlink/predictive_ML/models`              | List stored models                                            |
| GET    | `/downlink/predictive_ML/models/{model_name}` | Get model metadata                                            |
| POST   | `/downlink/predictive_ML/predict`             | Run future prediction                                         |
| DELETE | `/downlink/predictive_ML/models/{model_name}` | Delete stored model                                           |

---

# 🗄 Storage Architecture

* **Redis** → Model persistence
* **Pickle** → Model serialization
* **JSON** → Metadata storage
* **Redis Set** → Model registry
* Asset-based storage for:

  * Window length
  * Threshold configuration

---

# 🚀 Extensibility

The module is designed to be easily extended:

1. Add new algorithms inside:

```
ml/trainers/
```

2. Plug into:

```
train_service.py
```

3. Store models automatically via `model_store`
4. Reuse the existing prediction pipeline

---

# 📌 Summary

The **Predictive_ML** module provides a complete ML lifecycle:

```
Data → Processing → Training → Storage → Prediction → Version Management
```

Designed for:

* Scalable deployments
* Container-based environments
* Predictive maintenance systems

```

---

## If you want, I can next:
- Add **installation & setup steps**
- Add **example API request/response payloads**
- Add **Docker / environment configuration**
- Add **architecture diagram**
- Add **MLOps notes (retraining, monitoring, drift handling)**

Just tell me your target audience (developers, DevOps, data scientists, clients).
```
