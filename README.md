# Secure Healthcare Data Sharing System
## Using Blockchain, IPFS, and AI

A decentralized healthcare data sharing platform that enables secure storage, sharing, and AI-powered analysis of medical images.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Flask Templates)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Login   │  │  Upload  │  │ Download │  │   AI Diagnosis       │ │
│  │  Page    │  │  Medical │  │  Records │  │   Results            │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ACCESS CONTROL LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │    Roles     │  │  Permissions │  │   Session Management     │   │
│  │ Patient/Doc  │  │  View/Upload │  │   JWT Authentication     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│    DATA LAYER       │ │ BLOCKCHAIN LAYER│ │      AI LAYER           │
│ ┌─────────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────────────┐ │
│ │ AES Encryption  │ │ │ │   Blocks    │ │ │ │  Image Preprocessing│ │
│ │ (256-bit)       │ │ │ │ - PatientID │ │ │ │  - Resize           │ │
│ └─────────────────┘ │ │ │ - IPFS Hash │ │ │ │  - Normalize        │ │
│ ┌─────────────────┐ │ │ │ - Timestamp │ │ │ └─────────────────────┘ │
│ │ IPFS Storage    │ │ │ │ - Access    │ │ │ ┌─────────────────────┐ │
│ │ (via Infura)    │ │ │ │   Control   │ │ │ │  CNN/MobileNet      │ │
│ └─────────────────┘ │ │ └─────────────┘ │ │ │  Disease Detection  │ │
│ ┌─────────────────┐ │ │ ┌─────────────┐ │ │ └─────────────────────┘ │
│ │ File Handling   │ │ │ │  Consensus  │ │ │ ┌─────────────────────┐ │
│ │ Medical Images  │ │ │ │  Algorithm  │ │ │ │  Prediction Output  │ │
│ └─────────────────┘ │ │ └─────────────┘ │ │ │  - Disease Type     │ │
└─────────────────────┘ └─────────────────┘ │ │  - Confidence       │ │
                                            │ └─────────────────────┘ │
                                            └─────────────────────────┘
```

---

## Folder Structure

```
healthcare_blockchain/
│
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example                # Example environment file
│
├── modules/
│   ├── __init__.py
│   ├── data_layer/
│   │   ├── __init__.py
│   │   ├── encryption.py       # AES encryption/decryption
│   │   ├── ipfs_handler.py     # IPFS upload/download
│   │   └── file_handler.py     # Medical image processing
│   │
│   ├── blockchain/
│   │   ├── __init__.py
│   │   ├── blockchain.py       # Blockchain implementation
│   │   ├── block.py            # Block structure
│   │   └── consensus.py        # Consensus algorithm
│   │
│   ├── ai_layer/
│   │   ├── __init__.py
│   │   ├── model.py            # CNN/MobileNet model
│   │   ├── predictor.py        # Disease prediction
│   │   └── preprocessor.py     # Image preprocessing
│   │
│   └── access_control/
│       ├── __init__.py
│       ├── auth.py             # Authentication
│       ├── roles.py            # Role definitions
│       └── permissions.py      # Permission management
│
├── models/
│   └── disease_model.h5        # Trained AI model (placeholder)
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── records.html
│   ├── diagnosis.html
│   └── blockchain.html
│
├── uploads/                    # Temporary upload folder
├── downloads/                  # Downloaded files
│
└── tests/
    ├── test_encryption.py
    ├── test_blockchain.py
    └── test_ai.py
```

---

## Workflow

### 1. Patient Uploads Medical Image
```
Patient Login → Upload Image → AES Encrypt → Store in IPFS →
Record in Blockchain → Grant Access to Doctor
```

### 2. Doctor Views Patient Record
```
Doctor Login → Request Access → Verify Permission →
Retrieve from IPFS → AES Decrypt → View Image
```

### 3. AI Disease Detection
```
Select Image → Preprocess → Run CNN Model →
Get Prediction → Store Result in Blockchain
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python Flask |
| Database | SQLite (users) + Blockchain (records) |
| Storage | IPFS (via Infura) |
| Encryption | AES-256 (pyAesCrypt) |
| AI Model | TensorFlow/Keras (CNN → MobileNet) |
| Frontend | HTML/CSS/Bootstrap |
| Authentication | Flask-Login + JWT |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 3. Run the application
python app.py

# 4. Open browser
# http://localhost:5000
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/login` | GET/POST | User login |
| `/register` | GET/POST | User registration |
| `/dashboard` | GET | User dashboard |
| `/upload` | GET/POST | Upload medical image |
| `/records` | GET | View medical records |
| `/records/<id>` | GET | View specific record |
| `/diagnose/<id>` | POST | Run AI diagnosis |
| `/blockchain` | GET | View blockchain |
| `/grant-access` | POST | Grant access to record |
| `/api/chain` | GET | Get blockchain JSON |

---

## Brain MRI Dataset (Kaggle API)

You can train the AI model on Brain MRI data using KaggleHub.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

If you want training support, also install TensorFlow and NumPy:

```bash
pip install tensorflow numpy
```

### 2. Download + Train (one command)

```bash
python train_brain_mri.py --epochs 20 --batch-size 16 --model-type mobilenet --save-model models/brain_mri_model.keras
```

This uses the dataset:

```python
"navoneel/brain-mri-images-for-brain-tumor-detection"
```

### 3. Use trained model in app

Set model path in your environment or config to:

```bash
models/brain_mri_model.keras
```

Then restart the Flask app.

### 4. Important dataset check

For this Brain MRI dataset, expected classes are exactly:

```text
no
yes
```

The training script now validates this automatically and fails fast if folder root is wrong.
It also applies augmentation + early stopping + MobileNet fine-tuning by default.

---

## Chest X-ray Pneumonia Dataset (Kaggle API)

You can now train a dedicated binary X-ray model (Normal vs Pneumonia).

Dataset:

```python
"paultimothymooney/chest-xray-pneumonia"
```

Download-only snippet:

```python
import kagglehub

path = kagglehub.dataset_download("paultimothymooney/chest-xray-pneumonia")
print("Path to dataset files:", path)
```

Train command:

```bash
python train_chest_xray.py --epochs 20 --batch-size 16 --model-type mobilenet --save-model models/chest_xray_model.keras
```

If download gets interrupted on large files, increase retry attempts:

```bash
python train_chest_xray.py --download-retries 5 --save-model models/chest_xray_model.keras
```

If you already downloaded/extracted dataset manually, train from local path without Kaggle download:

```bash
python train_chest_xray.py --dataset-dir "C:/path/to/chest_xray"
```

Expected classes are validated automatically as:

```text
NORMAL
PNEUMONIA
```

After training, map it in `.env` so auto/manual diagnosis can use it:

```bash
AI_MODEL_REGISTRY={"brain_mri":"models/brain_mri_model.keras","mri":"models/brain_mri_model.keras","chest_xray":"models/chest_xray_model.keras","xray":"models/chest_xray_model.keras"}
```

---

## Chest CT-Scan Dataset (Kaggle API)

You can train a dedicated Chest CT model using:

```python
"mohamedhanyyy/chest-ctscan-images"
```

Download-only snippet:

```python
import kagglehub

path = kagglehub.dataset_download("mohamedhanyyy/chest-ctscan-images")
print("Path to dataset files:", path)
```

Train command:

```bash
python train_chest_ctscan.py --epochs 20 --batch-size 16 --model-type mobilenet --save-model models/chest_ctscan_model.keras
```

If download gets interrupted:

```bash
python train_chest_ctscan.py --download-retries 5 --save-model models/chest_ctscan_model.keras
```

If already downloaded/extracted manually:

```bash
python train_chest_ctscan.py --dataset-dir "C:/path/to/chest-ctscan-images"
```

After training, add it to model registry:

```bash
AI_MODEL_REGISTRY={"brain_mri":"models/brain_mri_model.keras","mri":"models/brain_mri_model.keras","chest_xray":"models/chest_xray_model.keras","xray":"models/chest_xray_model.keras","ct_scan":"models/chest_ctscan_model.keras","ct":"models/chest_ctscan_model.keras"}
```

---

## Breast Ultrasound Dataset (Kaggle API)

You can train a dedicated ultrasound model using:

```python
"aryashah2k/breast-ultrasound-images-dataset"
```

Download-only snippet:

```python
import kagglehub

path = kagglehub.dataset_download("aryashah2k/breast-ultrasound-images-dataset")
print("Path to dataset files:", path)
```

Train command:

```bash
python train_breast_ultrasound.py --epochs 20 --batch-size 16 --model-type mobilenet --save-model models/breast_ultrasound_model.keras
```

If download gets interrupted:

```bash
python train_breast_ultrasound.py --download-retries 5 --save-model models/breast_ultrasound_model.keras
```

If already downloaded/extracted manually:

```bash
python train_breast_ultrasound.py --dataset-dir "C:/path/to/breast-ultrasound-images-dataset"
```

After training, add it to model registry:

```bash
AI_MODEL_REGISTRY={"brain_mri":"models/brain_mri_model.keras","mri":"models/brain_mri_model.keras","chest_xray":"models/chest_xray_model.keras","xray":"models/chest_xray_model.keras","ct_scan":"models/chest_ctscan_model.keras","ct":"models/chest_ctscan_model.keras","ultrasound":"models/breast_ultrasound_model.keras","usg":"models/breast_ultrasound_model.keras"}
```

---

## Security Features

1. **Data Encryption**: AES-256 encryption before IPFS storage
2. **Access Control**: Role-based (Patient, Doctor, Admin)
3. **Blockchain**: Immutable audit trail
4. **IPFS**: Decentralized storage (no single point of failure)
5. **Session Security**: CSRF protection, secure cookies

---

## Future Upgrades

- [ ] Upgrade to Hyperledger Fabric
- [ ] Implement FOLS encryption (research-level)
- [ ] Add federated learning for AI
- [ ] Mobile app integration
- [ ] Multi-hospital network
