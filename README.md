# USER-APPLICATION-HONEYCOMB

## 📌 Overview
USER-APPLICATION-HONEYCOMB is a Python-based application designed to **fetch, manage, and process IoT device data** from **ChirpStack**. The system dynamically updates the device list and decodes incoming sensor data using predefined codecs.  

### **🚀 Key Features**
- **Device Management**: Fetches and maintains a dictionary (`all_devices`) with devices and their codecs.
- **Event Processing**: Listens to MQTT events from ChirpStack and decodes device payloads.
- **Automatic Updates**: A scheduler ensures newly added devices are fetched periodically.
- **Modular Design**: Well-structured code for better maintainability.
- **Asymmetric Ciphering Support**: Supports **ECDH ciphering** for secure encryption and decryption of device data.

---

## **📂 Project Structure**
```
USER-APPLICATION-HONEYCOMB/
🕠 __pycache__/               # Compiled Python files
🕠 .venv/                     # Virtual environment (if used)
🕠 old_code/                  # Backup of previous versions
🕠 .gitignore                 # Git ignore rules
🕠 application_fetcher.py      # Fetches applications from ChirpStack
🕠 codec_fetcher.py           # Retrieves codec information for devices
🕠 codec_struct_dec.py        # Decodes structured codec data
🕠 codec.js                   # JavaScript codec file
🕠 config.py                  # Stores configuration variables
🕠 device_fetcher.py          # Fetches devices from ChirpStack
🕠 device_manager.py          # Manages device storage and updates
🕠 downlink.py                # Handles downlink messaging
🕠 event_fetcher_parse.py     # Listens to MQTT events and decodes data
🕠 http_integration_fetcher.py# Handles HTTP integration with ChirpStack
🕠 key_rotation.py            # Manages key rotation for encryption
🕠 main.py                    # Starts the system (scheduler + MQTT listener)
🕠 README.md                  # Project documentation
🕠 requirements.txt           # Required dependencies
🕠 scheduler.py               # Periodically updates device list
🕠 send_http_request.py       # Handles sending HTTP requests
🕠 tenant_fetcher.py          # Fetches tenants from ChirpStack
```

---

## **📦 Installation & Setup**
### **1️⃣ Prerequisites**
Ensure you have:
- Python **3.10.12**
- ChirpStack MQTT broker running
- `pip` installed

### **2️⃣ Clone the Repository**
```sh
git clone https://github.com/your-repo/user-application-honeycomb.git
cd user-application-honeycomb
```

### **3️⃣ Create a Virtual Environment (Recommended)**
```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### **4️⃣ Install Dependencies**
```sh
pip install -r requirements.txt
```

### **5️⃣ Configure `config.py`**
Update `config.py` with your ChirpStack credentials:
```python
CHIRPSTACK_HOST = "localhost:8080"  # Update with your host
AUTH_METADATA = {"Authorization": "Bearer YOUR_TOKEN"}
```

---

## **🚀 How It Works**
### **🔹 Device Fetching & Management**
- `device_manager.py` **fetches and stores** devices in `all_devices` (key: `device_name`, value: `{euid, codec}`).
- `scheduler.py` **refreshes the device list every 10 minutes**.

### **🔹 MQTT Event Processing**
- `event_fetcher_parse.py` **subscribes to ChirpStack MQTT topics**.
- When an event arrives:
  - It extracts `dev_eui` and payload data.
  - It **matches `dev_eui` with `euid` in `all_devices`**.
  - It retrieves the **correct codec** and decodes the data.

---

## **📋 Running the Application**
Start the application by running:
```sh
python main.py
```
This will:
- Start **the scheduler** (to update the device list every 10 minutes).
- Start **the MQTT listener** (to process incoming sensor events).

---

## **⚙️ Code Breakdown**
### **1️⃣ `device_manager.py`**
Handles fetching and storing device information:
```python
device_manager.fetch_all_devices()  # Fetches all devices
device_manager.show_device_names()  # Displays the list of devices
```

### **2️⃣ `scheduler.py`**
Runs every **10 minutes** to update `all_devices`:
```python
schedule.every(10).minutes.do(scheduled_update)
```

### **3️⃣ `event_fetcher_parse.py`**
Listens for MQTT events and decodes messages:
```python
client.subscribe("application/+/device/+/event/+")
```
Matches `dev_eui` with `euid`:
```python
def get_device_codec(dev_eui):
    for device_name, device_info in device_manager.all_devices.items():
        if device_info.get("euid") == dev_eui:
            return device_info.get("codec")
    return None
```

---

## **🔧 Debugging & Logs**
Check **device updates**:
```sh
tail -f scheduler.log
```
Check **incoming MQTT messages**:
```sh
tail -f event_fetcher.log
```

---

## **📌 Future Enhancements**
- **Real-time WebSocket integration** for device updates.
- **Database storage** for historical events.
- **Custom decoders** for different device types.

---

## **📝 License**
This project is licensed under the **MIT License**.

---

## **👨‍💻 Contributing**
Pull requests are welcome! Open an issue for discussions.



## **Migrate Database For MFA(Existing instalaltions)**
---

# **Database Migration Guide (Alembic)**

This section explains how to set up and run a database migration using **Alembic** for the Honeycomb User Application.

---

## 🧩 **1. Install Dependencies**

Make sure you have a virtual environment activated, then install all required Python packages:

pip install -r requirements.txt

---

## ⚙️ **2. Initialize Alembic**

Create a new Alembic migration environment:

alembic init alembic

This will create a folder named **alembic/** and a configuration file **alembic.ini** in your project directory.

---

## 🛠️ **3. Configure Database URL**

Open the **alembic.ini** file and verify that the sqlalchemy.url line is configured correctly.

It should look like this (update values as per your local setup):

[alembic]
# ... don't change anything above ...

sqlalchemy.url = postgresql://myuser:mypassword@localhost:5434/mydatabase

---

## 🧬 **4. Update env.py**

Open the file **alembic/env.py** inside the alembic/ directory and make the following changes.

# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

### 🔹 Add these lines below under the above commented lines (After line 20):

from dotenv import load_dotenv
load_dotenv()

from auth.database import Base
target_metadata = Base.metadata

This ensures Alembic can detect your SQLAlchemy models and load environment variables from .env.

---

## 🧱 **5. Create a New Migration Revision**

Now, generate a new migration file to add a new column to the users table:

alembic revision -m "add mfa_secret to users"

This command will create a new file under **alembic/versions/**.

---

## ✏️ **6. Edit the Generated Revision**

Open the newly created migration file under **alembic/versions/**, and replace its content with the following:

def upgrade():
    op.add_column('users', sa.Column('mfa_secret', sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column('users', 'mfa_secret')

This defines what happens when you apply (upgrade) or revert (downgrade) the migration.

---

## 🚀 **7. Apply the Migration**

Run the migration to update your database schema:

alembic upgrade head

If successful, the new column mfa_secret will be added to the users table.

---


You’ve successfully completed the Alembic migration setup and applied your first migration.


---------For second Migration for email alert column----------

## 🧱 **1. Create a New Migration Revision**

Now, generate a new migration file to add a new column to the users table:

alembic revision -m "add loginalert email"

This command will create a new file under **alembic/versions/**.

---

## ✏️ **2. Edit the Generated Revision**

Open the newly created migration file under **alembic/versions/**, and replace its content with the following:

def upgrade():
    op.add_column('users', sa.Column('login_alert_email', sa.String(length=100), nullable=True))
    pass


def downgrade():
    op.drop_column('users', 'login_alert_email')
    pass

This defines what happens when you apply (upgrade) or revert (downgrade) the migration.

---

## 🚀 **3. Apply the Migration**

Run the migration to update your database schema:

alembic upgrade head

If successful, the new column login_alert_email will be added to the users table.

---

You’ve successfully completed the Alembic Second migration.