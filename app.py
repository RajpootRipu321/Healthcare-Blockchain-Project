"""
Secure Healthcare Data Sharing System
Main Flask Application

Features:
- Medical image upload with AES encryption
- IPFS decentralized storage
- Blockchain immutable records
- AI disease detection (CNN/MobileNet)
- Role-based access control
"""

import os
import json
import tempfile
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from config import Config
from modules.data_layer import AESCipher, IPFSHandler, LocalStorageHandler, FileHandler
from modules.blockchain import HealthcareBlockchain
from modules.ai_layer import DiseasePredictor, ImagePreprocessor
from modules.access_control import AuthManager, User, Role, Permission
from modules.access_control.auth import login_required, role_required, permission_required
from modules.consent import ConsentManager
from modules.prescriptions import PrescriptionManager, DURATION_PRESETS
from modules.chat.chat import ChatManager

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# CSRF Protection
csrf = CSRFProtect(app)

# Initialize components
auth_manager = AuthManager(db_path='healthcare.db')
consent_manager = ConsentManager(db_path='healthcare.db')
prescription_manager = PrescriptionManager(db_path='healthcare.db')
chat_manager = ChatManager(db_path='healthcare.db')

file_handler = FileHandler(
    upload_folder=app.config['UPLOAD_FOLDER'],
    download_folder=app.config['DOWNLOAD_FOLDER']
)
blockchain = HealthcareBlockchain(
    difficulty=app.config.get('DIFFICULTY', 4),
    node_address=app.config.get('GENESIS_NODE'),
    storage_path=app.config.get('BLOCKCHAIN_DATA_FILE')
)

# Initialize AI predictors (optional - works without TensorFlow)
def _parse_ai_model_registry() -> dict:
    """Parse configured model mapping from env/config."""
    registry = {}

    raw_registry = app.config.get('AI_MODEL_REGISTRY', '').strip()
    if not raw_registry:
        default_path = app.config.get('MODEL_PATH')
        if default_path:
            registry['default'] = default_path
        return registry

    try:
        parsed = json.loads(raw_registry)
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                if key and value:
                    registry[str(key).strip().lower()] = str(value).strip()
    except Exception:
        # Fallback syntax: key=path,key2=path2
        try:
            for pair in raw_registry.split(','):
                if '=' not in pair:
                    continue
                key, value = pair.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                if key and value:
                    registry[key] = value
        except Exception as e:
            print(f"AI model registry parse warning: {e}")

    return registry


def _load_trained_predictor(model_path: str):
    """Load predictor only if trained model file exists and loads correctly."""
    if not model_path or not os.path.exists(model_path):
        return None

    try:
        predictor = DiseasePredictor(model_path=model_path)
        if predictor.model_loaded:
            return predictor
    except Exception as e:
        print(f"AI model load warning for {model_path}: {e}")

    return None


AI_MODEL_PATHS = _parse_ai_model_registry()
AI_PREDICTORS = {}

for key, path in AI_MODEL_PATHS.items():
    predictor = _load_trained_predictor(path)
    if predictor:
        AI_PREDICTORS[key] = predictor

if AI_PREDICTORS:
    print(f"AI models loaded for keys: {', '.join(sorted(AI_PREDICTORS.keys()))}")
else:
    print("No trained AI model loaded. Diagnosis will use simulated analysis when needed.")


def _ordered_unique(values):
    seen = set()
    result = []
    for value in values:
        key = (value or '').strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _type_aliases(value: str):
    aliases = {
        'mri': ['brain_mri', 'mri'],
        'brain_mri': ['brain_mri', 'mri'],
        'xray': ['chest_xray', 'xray'],
        'chest_xray': ['chest_xray', 'xray'],
        'ct_scan': ['ct_scan', 'ct'],
        'ct': ['ct_scan', 'ct'],
        'ultrasound': ['ultrasound', 'usg'],
        'usg': ['ultrasound', 'usg'],
        'medical_image': ['general'],
        'general': ['general'],
    }
    return aliases.get(value, [value] if value else [])


def get_model_candidate_keys(record: dict = None, filename: str = "", diagnosis_profile: str = "") -> list:
    """Build model lookup keys from structured metadata and filename hints."""
    candidates = []

    if diagnosis_profile:
        candidates.extend(_type_aliases(str(diagnosis_profile).strip().lower()))

    if record:
        record_type = str(record.get('record_type', '')).strip().lower()
        if record_type:
            candidates.extend(_type_aliases(record_type))

        profile_from_meta = str(record.get('metadata', {}).get('diagnosis_profile', '')).strip().lower()
        if profile_from_meta:
            candidates.extend(_type_aliases(profile_from_meta))

        original_name = str(record.get('metadata', {}).get('original_filename', '')).strip().lower()
        if any(token in original_name for token in ['brain', 'tumor', 'mri']):
            candidates.extend(['brain_mri', 'mri'])
        if any(token in original_name for token in ['xray', 'x-ray', 'chest']):
            candidates.extend(['chest_xray', 'xray'])
        if 'ct' in original_name:
            candidates.extend(['ct_scan', 'ct'])
        if any(token in original_name for token in ['ultra', 'usg', 'sonography']):
            candidates.extend(['ultrasound', 'usg'])

    lower_name = (filename or '').strip().lower()
    if any(token in lower_name for token in ['brain', 'tumor', 'mri']):
        candidates.extend(['brain_mri', 'mri'])
    if any(token in lower_name for token in ['xray', 'x-ray', 'chest']):
        candidates.extend(['chest_xray', 'xray'])
    if 'ct' in lower_name:
        candidates.extend(['ct_scan', 'ct'])
    if any(token in lower_name for token in ['ultra', 'usg', 'sonography']):
        candidates.extend(['ultrasound', 'usg'])

    return _ordered_unique(candidates)


def get_ai_predictor_for_record(
    record: dict = None,
    filename: str = "",
    diagnosis_profile: str = "",
    manual_key: str = "",
    allow_default: bool = False
):
    """Pick predictor adaptively, or force with manual_key when supplied."""
    normalized_manual_key = (manual_key or '').strip().lower()
    if normalized_manual_key and normalized_manual_key not in {'auto', 'simulate'}:
        predictor = AI_PREDICTORS.get(normalized_manual_key)
        if predictor:
            return predictor, normalized_manual_key, get_model_candidate_keys(record, filename, diagnosis_profile)

    candidate_keys = get_model_candidate_keys(record, filename, diagnosis_profile)
    for key in candidate_keys:
        predictor = AI_PREDICTORS.get(key)
        if predictor:
            return predictor, key, candidate_keys

    if allow_default:
        predictor = AI_PREDICTORS.get('default')
        if predictor:
            return predictor, 'default', candidate_keys

    return None, None, candidate_keys


SIMULATED_PREDICTOR = DiseasePredictor(
    classes=['Normal', 'Pneumonia', 'COVID-19', 'Tuberculosis', 'Other']
)

# Initialize storage handler (IPFS with local fallback)
storage_handler = None
storage_mode = "local"  # Will be updated if IPFS works

try:
    # Test IPFS connection by making a simple API call
    ipfs = IPFSHandler()
    # Test the connection with a version check
    import requests
    test_url = "https://ipfs.infura.io:5001/api/v0/version"
    test_response = requests.post(test_url, headers=ipfs.headers, timeout=5)
    if test_response.status_code != 200:
        raise Exception(f"IPFS auth failed: {test_response.text}")
    storage_handler = ipfs
    storage_mode = "ipfs"
    print("IPFS storage (Infura) - Connected successfully!")
except Exception as e:
    print(f"IPFS not available: {e}")
    print("Using LOCAL storage mode (files stored in ipfs_storage/)")
    storage_handler = LocalStorageHandler(storage_folder='ipfs_storage')
    storage_mode = "local"


# ============== Helper Functions ==============

def get_current_user() -> User:
    """Get the currently logged in user."""
    if 'user_id' not in session:
        return None
    return auth_manager.get_user(session['user_id'])


def can_user_access_record(user: User, record: dict) -> bool:
    """Apply runtime access checks with consent enforcement for clinicians."""
    if not user or not record:
        return False

    if user.role == Role.ADMIN:
        return True

    if user.id == record.get('patient_id') or user.id == record.get('uploader_id'):
        return True

    # Doctors and researchers must have active consent, not just historical grant.
    if user.role in {Role.DOCTOR, Role.RESEARCHER}:
        return consent_manager.check_access(user.id, record.get('patient_id'), record.get('ipfs_hash'))

    return user.id in set(record.get('access_list', []))


def get_all_records_unrestricted() -> list:
    """Collect all records without applying user-level filtering."""
    records = []
    for block in blockchain.chain:
        for record in block.records:
            records.append({
                'block_index': block.index,
                **record.to_dict()
            })
    return records


def get_record_by_hash_unrestricted(ipfs_hash: str) -> dict:
    """Find a record by hash without access-list checks."""
    for block in blockchain.chain:
        for record in block.records:
            if record.ipfs_hash == ipfs_hash:
                return {
                    'block_index': block.index,
                    **record.to_dict()
                }
    return None


def sync_doctor_record_access(user: User):
    """Backfill record-level grants from active consents for doctor/researcher users."""
    if not user or user.role not in {Role.DOCTOR, Role.RESEARCHER}:
        return

    active_consents = consent_manager.get_accessible_patients(user.id)
    for consent in active_consents:
        patient_id = consent.get('patient_id')
        record_hash = consent.get('record_hash')

        if record_hash == 'all':
            blockchain.grant_access_to_patient_records(
                patient_id=patient_id,
                owner_id=patient_id,
                target_user_id=user.id
            )
        elif record_hash:
            blockchain.grant_access(record_hash, patient_id, user.id)


def get_records_for_user(user: User) -> list:
    """Get all records visible to a user under runtime policy checks."""
    if not user:
        return []

    # Keep doctor access-list in sync with approved active consent.
    sync_doctor_record_access(user)

    if user.role in {Role.ADMIN, Role.DOCTOR, Role.RESEARCHER}:
        all_records = get_all_records_unrestricted()
        return [r for r in all_records if can_user_access_record(user, r)]

    own_records = blockchain.get_all_records(user.id)
    return [r for r in own_records if can_user_access_record(user, r)]


# ============== Routes ==============

# ============== Chat Helpers ==============

def get_chat_contact(user: User, contact_id: str):
    """
    Return the requested chat contact only when the current user
    has a valid Doctor <-> Patient consent relationship with them.
    """
    if not user or user.role not in {Role.DOCTOR, Role.PATIENT}:
        return None

    contact = auth_manager.get_user(contact_id)

    if not contact or not contact.is_active:
        return None

    # Chat is strictly Doctor <-> Patient.
    if user.role == Role.DOCTOR:
        if contact.role != Role.PATIENT:
            return None

        # Doctor can chat only with patients for whom active consent exists.
        if not consent_manager.check_access(
            user.id,
            contact.id
        ):
            return None

    elif user.role == Role.PATIENT:
        if contact.role != Role.DOCTOR:
            return None

        # Patient can chat only with doctors who currently have
        # active consent for this patient.
        if not consent_manager.check_access(
            contact.id,
            user.id
        ):
            return None

    return contact


def get_chat_contacts(user: User):
    """
    Get only valid Doctor <-> Patient chat contacts.

    Doctors:
        Patients with active consent.

    Patients:
        Doctors with active consent.
    """
    if not user or user.role not in {Role.DOCTOR, Role.PATIENT}:
        return []

    contacts = []

    if user.role == Role.DOCTOR:
        accessible_patients = consent_manager.get_accessible_patients(user.id)

        for patient_info in accessible_patients:
            patient = auth_manager.get_user(patient_info['patient_id'])

            if not patient or not patient.is_active:
                continue

            if patient.role != Role.PATIENT:
                continue

            last_message = chat_manager.get_last_message(
                user.id,
                patient.id
            )

            contacts.append({
                'id': patient.id,
                'name': patient.full_name or patient.username,
                'username': patient.username,
                'role': patient.role.value,
                'last_message': (
                    last_message['message']
                    if last_message else None
                ),
                'unread_count': chat_manager.get_unread_count(
                    user.id,
                    patient.id
                )
            })

    elif user.role == Role.PATIENT:
        active_consents = consent_manager.get_active_consents_for_patient(
            user.id
        )

        seen_doctors = set()

        for consent in active_consents:
            doctor_id = consent.get('doctor_id')

            if not doctor_id or doctor_id in seen_doctors:
                continue

            seen_doctors.add(doctor_id)

            doctor = auth_manager.get_user(doctor_id)

            if not doctor or not doctor.is_active:
                continue

            if doctor.role != Role.DOCTOR:
                continue

            # Re-check consent so expired/revoked access cannot
            # accidentally appear as a chat contact.
            if not consent_manager.check_access(
                doctor.id,
                user.id
            ):
                continue

            last_message = chat_manager.get_last_message(
                user.id,
                doctor.id
            )

            contacts.append({
                'id': doctor.id,
                'name': doctor.full_name or doctor.username,
                'username': doctor.username,
                'role': doctor.role.value,
                'last_message': (
                    last_message['message']
                    if last_message else None
                ),
                'unread_count': chat_manager.get_unread_count(
                    user.id,
                    doctor.id
                )
            })

    return contacts

@app.route('/')
def index():
    """Home page."""
    return render_template('index.html', user=get_current_user())


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name', '')
        role = request.form.get('role', 'patient')

        # Validation
        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        # Register user
        user = auth_manager.register(username, email, password, role, full_name)

        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists.', 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = auth_manager.login(username, password)

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role.value
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            if user.role == Role.PHARMACIST:
                return redirect(url_for('pharmacist_search'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user = get_current_user()
    if user and user.role == Role.PHARMACIST:
        return redirect(url_for('pharmacist_search'))
    records = get_records_for_user(user) if user else []

    return render_template('dashboard.html',
                           user=user,
                           records=records,
                           total_records=len(records))


# ============== Chat Routes ==============

@app.route('/chat')
@login_required
@role_required(Role.DOCTOR, Role.PATIENT)
def chat():
    """
    Main chat page.

    Chat is available only to doctors and patients.
    Contacts are limited to active consent relationships.
    """
    user = get_current_user()

    contacts = get_chat_contacts(user)

    active_contact = None
    messages = []

    contact_id = request.args.get('contact_id')

    if contact_id:
        active_contact = get_chat_contact(user, contact_id)

        if not active_contact:
            flash(
                'You do not have an active chat relationship with this user.',
                'danger'
            )
            return redirect(url_for('chat'))

        messages = chat_manager.get_conversation(
            user.id,
            active_contact.id
        )

        # Opening a conversation marks received messages as read.
        chat_manager.mark_read(
            user.id,
            active_contact.id
        )

    return render_template(
        'chat.html',
        user=user,
        contacts=contacts,
        active_contact=active_contact,
        messages=messages
    )


@app.route('/chat/<contact_id>')
@login_required
@role_required(Role.DOCTOR, Role.PATIENT)
def chat_thread(contact_id):
    """
    Open a specific Doctor <-> Patient conversation.
    """
    user = get_current_user()

    contact = get_chat_contact(user, contact_id)

    if not contact:
        flash(
            'You do not have an active chat relationship with this user.',
            'danger'
        )
        return redirect(url_for('chat'))

    return redirect(
        url_for(
            'chat',
            contact_id=contact.id
        )
    )


@app.route('/chat/<contact_id>/send', methods=['POST'])
@login_required
@role_required(Role.DOCTOR, Role.PATIENT)
def send_chat_message(contact_id):
    """
    Send a chat message.

    The relationship is checked again here. This is intentional:
    hiding the menu/contact is NOT considered a security control.
    """
    user = get_current_user()

    contact = get_chat_contact(user, contact_id)

    if not contact:
        return jsonify({
            'error': 'You do not have permission to chat with this user.'
        }), 403

    message = request.form.get('message', '').strip()

    if not message:
        return jsonify({
            'error': 'Message cannot be empty.'
        }), 400

    if len(message) > 4000:
        return jsonify({
            'error': 'Message is too long.'
        }), 400

    stored_message = chat_manager.send_message(
        sender_id=user.id,
        receiver_id=contact.id,
        message=message
    )

    if not stored_message:
        return jsonify({
            'error': 'Could not send message.'
        }), 400

    return jsonify({
        'message': stored_message
    }), 201


@app.route('/api/chat/<contact_id>/messages')
@login_required
@role_required(Role.DOCTOR, Role.PATIENT)
def chat_messages(contact_id):
    """
    Poll for new messages in a Doctor <-> Patient conversation.
    """
    user = get_current_user()

    contact = get_chat_contact(user, contact_id)

    if not contact:
        return jsonify({
            'error': 'You do not have permission to access this conversation.'
        }), 403

    try:
        since_id = int(request.args.get('since_id', 0))
    except (TypeError, ValueError):
        since_id = 0

    messages = chat_manager.get_messages_since(
        user.id,
        contact.id,
        since_id=since_id
    )

    # Polling the conversation also marks received messages as read.
    chat_manager.mark_read(
        user.id,
        contact.id
    )

    return jsonify({
        'messages': messages
    })

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload medical image."""
    user = get_current_user()

    if request.method == 'POST':
        # Check if file in request
        if 'file' not in request.files:
            flash('No file selected.', 'danger')
            return render_template('upload.html', user=user)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected.', 'danger')
            return render_template('upload.html', user=user)

        # Get form data
        patient_id = request.form.get('patient_id', user.id)
        encryption_key = request.form.get('encryption_key')
        record_type = request.form.get('record_type', 'medical_image')
        diagnosis_profile = request.form.get('diagnosis_profile', '').strip().lower()

        if not encryption_key:
            flash('Encryption key is required.', 'danger')
            return render_template('upload.html', user=user)

        try:
            # Save file temporarily
            file_path, original_name = file_handler.save_upload(file, patient_id)

            # Encrypt file
            cipher = AESCipher(encryption_key)
            encrypted_path = cipher.encrypt_file(file_path)

            # Upload to storage (IPFS or local)
            result = storage_handler.upload_file(encrypted_path)
            ipfs_hash = result['Hash']

            # Add to blockchain
            block_index = blockchain.add_record(
                patient_id=patient_id,
                ipfs_hash=ipfs_hash,
                uploader_id=user.id,
                record_type=record_type,
                metadata={
                    'original_filename': original_name,
                    'encrypted': True,
                    'storage_mode': storage_mode,
                    'diagnosis_profile': diagnosis_profile
                }
            )

            # Auto-share newly uploaded data with currently active consent holders.
            active_consents = consent_manager.get_active_consents_for_patient(patient_id)
            for consent in active_consents:
                consent_record_hash = consent.get('record_hash', 'all')
                if consent_record_hash in {'all', ipfs_hash}:
                    blockchain.grant_access(ipfs_hash, user.id, consent['doctor_id'])

            # Cleanup temp files
            file_handler.cleanup_temp_files([file_path, encrypted_path])

            flash(f'File uploaded successfully! Hash: {ipfs_hash}', 'success')
            flash(f'Added to Block #{block_index} (Storage: {storage_mode.upper()})', 'info')

        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'danger')

    return render_template('upload.html', user=user)


@app.route('/records')
@login_required
def records():
    """View medical records."""
    user = get_current_user()
    user_records = get_records_for_user(user)

    return render_template('records.html', user=user, records=user_records)


@app.route('/download/<ipfs_hash>', methods=['GET', 'POST'])
@login_required
def download(ipfs_hash):
    """Download a medical record."""
    user = get_current_user()

    # Check access
    record = get_record_by_hash_unrestricted(ipfs_hash)
    if not record or not can_user_access_record(user, record):
        flash('Record not found or access denied.', 'danger')
        return redirect(url_for('records'))

    if request.method == 'POST':
        encryption_key = request.form.get('encryption_key')

        if not encryption_key:
            flash('Encryption key is required.', 'danger')
            return render_template('download.html', user=user, record=record)

        try:
            # Download from storage
            temp_encrypted = os.path.join(
                app.config['DOWNLOAD_FOLDER'],
                f"{ipfs_hash}.enc"
            )
            storage_handler.download_file(ipfs_hash, temp_encrypted)

            # Decrypt file
            original_name = record.get('metadata', {}).get('original_filename', 'download')
            output_path = os.path.join(
                app.config['DOWNLOAD_FOLDER'],
                original_name
            )

            cipher = AESCipher(encryption_key)
            cipher.decrypt_file(temp_encrypted, output_path)

            # Cleanup encrypted temp file
            os.remove(temp_encrypted)

            flash('File decrypted successfully!', 'success')
            return send_file(output_path, as_attachment=True)

        except Exception as e:
            flash(f'Download failed: {str(e)}', 'danger')

    return render_template('download.html', user=user, record=record)


@app.route('/diagnose/<ipfs_hash>', methods=['GET', 'POST'])
@login_required
def diagnose(ipfs_hash):
    """Run AI diagnosis on a medical image."""
    user = get_current_user()

    # Check if user has permission
    if not user.has_permission(Permission.RUN_DIAGNOSIS):
        flash('You do not have permission to run diagnoses.', 'danger')
        return redirect(url_for('records'))

    record = get_record_by_hash_unrestricted(ipfs_hash)
    if not record or not can_user_access_record(user, record):
        flash('Record not found or access denied.', 'danger')
        return redirect(url_for('records'))

    diagnosis_result = None
    available_model_keys = sorted(AI_PREDICTORS.keys())
    auto_candidate_keys = get_model_candidate_keys(record=record)
    selected_model = 'auto'

    if request.method == 'POST':
        encryption_key = request.form.get('encryption_key')
        selected_model = request.form.get('model_key', 'auto').strip().lower()

        if not encryption_key:
            flash('Encryption key is required for diagnosis.', 'danger')
            return render_template('diagnosis.html', user=user, record=record)

        try:
            record_type = str(record.get('record_type', '')).strip().lower()
            allow_default = record_type in {'medical_image', '', 'other_medical_image', 'general'}

            predictor, predictor_key, auto_candidate_keys = get_ai_predictor_for_record(
                record=record,
                manual_key=selected_model,
                allow_default=allow_default
            )
            if predictor:
                # Download and decrypt temporarily
                enc_fd, temp_encrypted_path = tempfile.mkstemp(suffix='.enc')
                dec_fd, temp_decrypted_path = tempfile.mkstemp(suffix='.png')
                os.close(enc_fd)
                os.close(dec_fd)

                storage_handler.download_file(ipfs_hash, temp_encrypted_path)

                cipher = AESCipher(encryption_key)
                cipher.decrypt_file(temp_encrypted_path, temp_decrypted_path)

                # Run AI prediction
                diagnosis_result = predictor.predict(temp_decrypted_path)
                diagnosis_result['model_key'] = predictor_key

                # Cleanup
                os.unlink(temp_encrypted_path)
                os.unlink(temp_decrypted_path)

                if selected_model not in {'', 'auto'} and predictor_key == selected_model:
                    flash(f'Diagnosis completed using manually selected model ({predictor_key}).', 'success')
                else:
                    flash(f'Diagnosis completed using trained model ({predictor_key}).', 'success')

            else:
                # Download and decrypt for simulated prediction
                enc_fd, temp_encrypted_path = tempfile.mkstemp(suffix='.enc')
                dec_fd, temp_decrypted_path = tempfile.mkstemp(suffix='.png')
                os.close(enc_fd)
                os.close(dec_fd)

                storage_handler.download_file(ipfs_hash, temp_encrypted_path)

                cipher = AESCipher(encryption_key)
                cipher.decrypt_file(temp_encrypted_path, temp_decrypted_path)

                if selected_model == 'simulate':
                    flash('Diagnosis completed in simulation mode by manual selection.', 'info')
                elif selected_model not in {'', 'auto'}:
                    flash(f'Model "{selected_model}" is not loaded. Using simulated prediction.', 'warning')
                else:
                    flash('No trained model matched this record. Using simulated prediction.', 'warning')
                diagnosis_result = SIMULATED_PREDICTOR.predict(temp_decrypted_path)
                diagnosis_result['model_key'] = 'simulate'

                # Cleanup
                os.unlink(temp_encrypted_path)
                os.unlink(temp_decrypted_path)

        except Exception as e:
            flash(f'Diagnosis failed: {str(e)}', 'danger')

    return render_template('diagnosis.html',
                           user=user,
                           record=record,
                           diagnosis=diagnosis_result,
                           available_model_keys=available_model_keys,
                           auto_candidate_keys=auto_candidate_keys,
                           selected_model=selected_model)


@app.route('/grant-access', methods=['POST'])
@login_required
def grant_access():
    """Grant access to a record."""
    user = get_current_user()

    if not user.has_permission(Permission.GRANT_ACCESS):
        flash('You do not have permission to grant access.', 'danger')
        return redirect(url_for('records'))

    ipfs_hash = request.form.get('ipfs_hash')
    target_user_id = request.form.get('target_user_id')

    if blockchain.grant_access(ipfs_hash, user.id, target_user_id):
        flash('Access granted successfully.', 'success')
    else:
        flash('Failed to grant access.', 'danger')

    return redirect(url_for('records'))


@app.route('/organizations', methods=['GET', 'POST'])
@login_required
def organizations():
    """Create or join healthcare organizations."""
    user = get_current_user()

    if request.method == 'POST':
        action = request.form.get('action', '').strip().lower()

        if action == 'create':
            name = request.form.get('name', '').strip()
            org_type = request.form.get('org_type', '').strip()
            address = request.form.get('address', '').strip()
            license_number = request.form.get('license_number', '').strip()

            if not all([name, org_type, license_number]):
                flash('Name, type and license number are required.', 'danger')
            else:
                try:
                    org = consent_manager.create_organization(
                        name=name,
                        org_type=org_type,
                        address=address,
                        license_number=license_number
                    )
                    consent_manager.add_user_to_organization(user.id, org.id, role='owner')
                    flash('Organization created and linked to your account.', 'success')
                except Exception as e:
                    flash(f'Failed to create organization: {str(e)}', 'danger')

        elif action == 'join':
            org_id = request.form.get('organization_id', '').strip()
            membership_role = request.form.get('membership_role', 'member').strip()
            if not org_id:
                flash('Please select an organization to join.', 'danger')
            else:
                consent_manager.add_user_to_organization(user.id, org_id, membership_role)
                flash('Organization linked successfully.', 'success')

        return redirect(url_for('organizations'))

    organizations_list = consent_manager.get_all_organizations()
    user_org = consent_manager.get_user_organization(user.id)
    owned_orgs = consent_manager.get_owned_organizations(user.id)

    return render_template(
        'organizations.html',
        user=user,
        organizations=organizations_list,
        user_org=user_org,
        owned_orgs=owned_orgs
    )


# ============== Organization Staff (Pharmacist accounts) ==============

@app.route('/organizations/staff', methods=['GET', 'POST'])
@login_required
def organization_staff():
    """
    Org owners create Pharmacist accounts, scoped to an org they own.
    Not gated by role_required(Role.ADMIN) - "org owner" is a per-organization
    membership flag (user_organizations.role == 'owner'), not the global
    Role.ADMIN. Any user who owns at least one organization can reach this.
    """
    user = get_current_user()
    owned_orgs = consent_manager.get_owned_organizations(user.id)

    if not owned_orgs:
        flash('Only an organization owner can manage staff accounts.', 'danger')
        return redirect(url_for('organizations'))

    owned_org_ids = {o.id for o in owned_orgs}

    if request.method == 'POST':
        org_id = request.form.get('organization_id', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        if org_id not in owned_org_ids:
            flash('You can only create staff for organizations you own.', 'danger')
        elif not all([org_id, username, email, password]):
            flash('All fields are required.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            new_staff = auth_manager.register(username, email, password,
                                               role='pharmacist', full_name=full_name)
            if new_staff:
                consent_manager.add_user_to_organization(new_staff.id, org_id, role='member')
                flash(f'Pharmacist account "{username}" created.', 'success')
            else:
                flash('Username or email already exists.', 'danger')

        return redirect(url_for('organization_staff'))

    # Group existing pharmacist accounts by the org they belong to, filtered
    # to orgs this user owns. Filtered in Python rather than a raw SQL join,
    # matching the existing get_doctors()-style pattern in AuthManager.
    all_pharmacists = [u for u in auth_manager.get_all_users() if u.role == Role.PHARMACIST]
    staff_by_org = {org.id: [] for org in owned_orgs}
    for pharmacist in all_pharmacists:
        p_org = consent_manager.get_user_organization(pharmacist.id)
        if p_org and p_org.id in owned_org_ids:
            staff_by_org[p_org.id].append(pharmacist)

    return render_template(
        'organization_staff.html',
        user=user,
        owned_orgs=owned_orgs,
        staff_by_org=staff_by_org
    )


# ============== Prescriptions ==============

@app.route('/prescriptions/write', methods=['GET', 'POST'])
@login_required
@role_required(Role.DOCTOR)
def write_prescription():
    """Doctor writes a prescription for a patient they are currently consulting."""
    user = get_current_user()
    patients = consent_manager.get_accessible_patients(user.id)
    doctor_orgs = consent_manager.get_user_organizations(user.id)

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', '').strip()
        org_id = request.form.get('organization_id', '').strip()
        content = request.form.get('content', '').strip()
        duration_key = request.form.get('duration_key', '').strip()

        patient_record = next((p for p in patients if p['patient_id'] == patient_id), None)
        org_record = next((o for o in doctor_orgs if o.id == org_id), None)

        if not patient_record:
            flash('You can only prescribe for patients you are currently consulting.', 'danger')
        elif not org_record:
            flash('Please select a valid organization you belong to.', 'danger')
        elif not content:
            flash('Prescription content cannot be empty.', 'danger')
        elif duration_key not in DURATION_PRESETS:
            flash('Please select a valid course duration.', 'danger')
        else:
            rx = prescription_manager.create_prescription(
                doctor_id=user.id,
                doctor_name=user.full_name or user.username,
                patient_id=patient_id,
                patient_name=patient_record['patient_name'],
                org_id=org_record.id,
                org_name=org_record.name,
                content=content,
                duration_key=duration_key
            )
            if rx:
                flash(f'Prescription {rx["rx_uid"]} created for {rx["patient_name"]}.', 'success')
            else:
                flash('Could not create prescription. Please check your inputs.', 'danger')

        return redirect(url_for('write_prescription'))

    recent_prescriptions = prescription_manager.get_for_doctor(user.id, limit=20)

    return render_template(
        'prescription_write.html',
        user=user,
        patients=patients,
        doctor_orgs=doctor_orgs,
        duration_presets=DURATION_PRESETS,
        recent_prescriptions=recent_prescriptions
    )


@app.route('/prescriptions')
@login_required
@role_required(Role.PATIENT)
def view_prescriptions():
    """Patient's paginated prescription history, newest first."""
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    result = prescription_manager.get_for_patient(user.id, page=page, per_page=10)

    return render_template('prescription_patient.html', user=user, **result)


# ============== Pharmacist (single page, org-scoped) ==============

@app.route('/pharmacist')
@login_required
@role_required(Role.PHARMACIST)
def pharmacist_search():
    """The only page a Pharmacist ever sees: search + dispense by rx_uid."""
    user = get_current_user()
    org = consent_manager.get_user_organization(user.id)

    rx_uid = request.args.get('rx_uid', '').strip()
    result = None
    searched = bool(rx_uid)

    if rx_uid and org:
        result = prescription_manager.find_for_pharmacist(rx_uid, org.id)

    return render_template(
        'pharmacist.html',
        user=user,
        org=org,
        rx_uid=rx_uid,
        result=result,
        searched=searched
    )


@app.route('/pharmacist/dispense', methods=['POST'])
@login_required
@role_required(Role.PHARMACIST)
def pharmacist_dispense():
    """Mark a prescription as dispensed (status: not_started -> started)."""
    user = get_current_user()
    org = consent_manager.get_user_organization(user.id)
    rx_uid = request.form.get('rx_uid', '').strip()

    if not org:
        flash('Your account is not linked to an organization. Contact your admin.', 'danger')
    else:
        updated = prescription_manager.mark_started(rx_uid, org.id, user.id)
        if updated:
            flash(f'Prescription {updated["rx_uid"]} marked as dispensed.', 'success')
        else:
            flash('Could not dispense this prescription (not found, wrong organization, or already handled).', 'danger')

    return redirect(url_for('pharmacist_search', rx_uid=rx_uid))


@app.route('/request-access', methods=['GET', 'POST'])
@login_required
@role_required(Role.DOCTOR, Role.ADMIN)
def request_access():
    """Doctor requests access to patient records."""
    user = get_current_user()
    user_org = consent_manager.get_user_organization(user.id)

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', '').strip()
        reason = request.form.get('reason', '').strip()
        access_type = request.form.get('access_type', 'view').strip()
        record_hash = request.form.get('record_hash', 'all').strip() or 'all'

        patient = auth_manager.get_user(patient_id)
        if not patient or patient.role != Role.PATIENT:
            flash('Invalid patient selected.', 'danger')
            return redirect(url_for('request_access'))

        if not reason:
            flash('Please provide a reason for access request.', 'danger')
            return redirect(url_for('request_access'))

        if not user_org:
            flash('Join an organization first before requesting cross-hospital access.', 'warning')
            return redirect(url_for('organizations'))

        if not consent_manager.is_hospital_allowed_for_patient(patient_id, user_org.id):
            flash('Patient policy does not allow data sharing with your organization.', 'danger')
            return redirect(url_for('request_access'))

        consent_manager.create_access_request(
            doctor_id=user.id,
            doctor_name=user.full_name or user.username,
            patient_id=patient.id,
            patient_name=patient.full_name or patient.username,
            reason=reason,
            access_type=access_type,
            record_hash=record_hash,
            organization_id=user_org.id,
            organization_name=user_org.name
        )

        flash('Access request submitted to patient for approval.', 'success')
        return redirect(url_for('request_access'))

    search_term = request.args.get('q', '').strip()
    patient_results = consent_manager.search_patients(search_term, auth_manager) if search_term else []
    doctor_requests = consent_manager.get_requests_by_doctor(user.id)
    accessible_patients = consent_manager.get_accessible_patients(user.id)

    return render_template(
        'doctor_access.html',
        user=user,
        search_term=search_term,
        patient_results=patient_results,
        doctor_requests=doctor_requests,
        accessible_patients=accessible_patients,
        user_org=user_org
    )


@app.route('/consent-center')
@login_required
@role_required(Role.PATIENT, Role.ADMIN)
def consent_center():
    """Patient consent management center."""
    user = get_current_user()

    pending_requests = consent_manager.get_pending_requests_for_patient(user.id)
    active_consents = consent_manager.get_active_consents_for_patient(user.id)
    policy = consent_manager.get_patient_hospital_policy(user.id)
    organizations_list = consent_manager.get_all_organizations()

    return render_template(
        'consent_center.html',
        user=user,
        pending_requests=pending_requests,
        active_consents=active_consents,
        policy=policy,
        organizations=organizations_list
    )


@app.route('/consent-policy', methods=['POST'])
@login_required
@role_required(Role.PATIENT, Role.ADMIN)
def update_consent_policy():
    """Update patient organization sharing policy."""
    user = get_current_user()
    mode = request.form.get('mode', 'allow_all').strip()
    organization_ids = request.form.getlist('organization_ids')

    if mode != 'allow_selected':
        organization_ids = []

    if consent_manager.set_patient_hospital_policy(user.id, mode, organization_ids):
        flash('Sharing policy updated successfully.', 'success')
    else:
        flash('Failed to update sharing policy.', 'danger')

    return redirect(url_for('consent_center'))


@app.route('/approve-request/<request_id>', methods=['POST'])
@login_required
@role_required(Role.PATIENT, Role.ADMIN)
def approve_request(request_id):
    """Approve a doctor's access request and grant record-level access."""
    user = get_current_user()
    duration_days = int(request.form.get('duration_days', 30))
    notes = request.form.get('notes', '').strip()

    access_request = consent_manager.get_request_by_id(request_id)
    if not access_request or access_request.patient_id != user.id:
        flash('Access request not found.', 'danger')
        return redirect(url_for('consent_center'))

    if access_request.organization_id and not consent_manager.is_hospital_allowed_for_patient(
        user.id, access_request.organization_id
    ):
        flash('Requesting organization is blocked by your sharing policy.', 'danger')
        return redirect(url_for('consent_center'))

    if not consent_manager.approve_request(request_id, user.id, duration_days=duration_days, notes=notes):
        flash('Could not approve request.', 'danger')
        return redirect(url_for('consent_center'))

    # Align blockchain access-list with consent grant.
    if access_request.record_hash == 'all':
        granted = blockchain.grant_access_to_patient_records(
            patient_id=user.id,
            owner_id=user.id,
            target_user_id=access_request.doctor_id
        )
    else:
        granted = 1 if blockchain.grant_access(
            access_request.record_hash,
            user.id,
            access_request.doctor_id
        ) else 0

    if granted == 0:
        flash('Consent approved, but no matching records were found to grant.', 'warning')
    else:
        flash(f'Request approved. Access granted to {granted} record(s).', 'success')

    return redirect(url_for('consent_center'))


@app.route('/deny-request/<request_id>', methods=['POST'])
@login_required
@role_required(Role.PATIENT, Role.ADMIN)
def deny_request(request_id):
    """Deny a pending access request."""
    user = get_current_user()
    notes = request.form.get('notes', '').strip()

    if consent_manager.deny_request(request_id, user.id, notes=notes):
        flash('Request denied.', 'info')
    else:
        flash('Could not deny request.', 'danger')

    return redirect(url_for('consent_center'))


@app.route('/revoke-consent/<consent_id>', methods=['POST'])
@login_required
@role_required(Role.PATIENT, Role.ADMIN)
def revoke_consent(consent_id):
    """Revoke previously granted consent and remove record-level access."""
    user = get_current_user()
    consent = consent_manager.get_active_consent_by_id(consent_id, patient_id=user.id)

    if not consent:
        flash('Consent entry not found.', 'danger')
        return redirect(url_for('consent_center'))

    if not consent_manager.revoke_access(consent_id, user.id):
        flash('Could not revoke access.', 'danger')
        return redirect(url_for('consent_center'))

    record_hash = None if consent['record_hash'] == 'all' else consent['record_hash']
    revoked = blockchain.revoke_access_for_patient_records(
        patient_id=user.id,
        owner_id=user.id,
        target_user_id=consent['doctor_id'],
        record_hash=record_hash
    )

    flash(f'Consent revoked. Removed access from {revoked} record(s).', 'warning')
    return redirect(url_for('consent_center'))


@app.route('/blockchain')
@login_required
def view_blockchain():
    """View the blockchain."""
    user = get_current_user()
    chain_data = blockchain.to_dict()

    return render_template('blockchain.html',
                           user=user,
                           chain=chain_data['chain'],
                           length=chain_data['length'])


# ============== API Endpoints ==============

@app.route('/api/chain', methods=['GET'])
def api_get_chain():
    """API: Get blockchain data."""
    return jsonify(blockchain.to_dict())


@app.route('/api/records', methods=['GET'])
@login_required
def api_get_records():
    """API: Get user's records."""
    user = get_current_user()
    records = get_records_for_user(user)
    return jsonify({'records': records})


@app.route('/api/diagnose', methods=['POST'])
@login_required
def api_diagnose():
    """API: Run diagnosis on uploaded image."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    try:
        # Save temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)

        # Run prediction
        model_key = request.form.get('model_key', 'auto').strip().lower()
        record_type = request.form.get('record_type', '').strip().lower()
        diagnosis_profile = request.form.get('diagnosis_profile', '').strip().lower()
        allow_default = record_type in {'medical_image', '', 'other_medical_image', 'general'}

        predictor, predictor_key, candidate_keys = get_ai_predictor_for_record(
            filename=file.filename,
            diagnosis_profile=diagnosis_profile or record_type,
            manual_key=model_key,
            allow_default=allow_default
        )
        if predictor:
            result = predictor.predict(temp_path)
            result['model_key'] = predictor_key
        else:
            result = SIMULATED_PREDICTOR.predict(temp_path)
            result['model_key'] = 'simulate'

        result['candidate_keys'] = candidate_keys

        # Cleanup
        os.remove(temp_path)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============== Error Handlers ==============

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16MB.', 'danger')
    return redirect(url_for('upload'))


# ============== Main ==============

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('models', exist_ok=True)

    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)