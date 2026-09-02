# Abstract

This project implements a decentralized and security-focused file sharing system with a healthcare-oriented extension. The codebase combines blockchain-based record tracking, encrypted file storage, decentralized content addressing, role-aware access control, and optional AI-assisted diagnosis workflows for medical images.

At its core, the system separates storage and integrity responsibilities. Files are encrypted before storage, and only content identifiers and metadata are recorded in blockchain blocks. This design reduces direct on-chain storage overhead while preserving traceability and tamper-evident record history. The repository contains multiple server components and a healthcare-specific Flask application with modular layers for data handling, blockchain logic, AI prediction, and authentication/authorization.

The project demonstrates practical implementation concerns rather than only conceptual design. It includes endpoint-driven workflows for registration, login, upload, download, record viewing, blockchain state access, and diagnosis operations. It also includes dataset-aware training scripts for multiple imaging domains such as brain MRI, chest X-ray, chest CT-scan, and breast ultrasound. The architecture supports operation with external IPFS services when available and local fallback mechanisms when external dependency checks fail.

From an engineering perspective, the implemented system emphasizes: secure file lifecycle management, explicit role permissions, deterministic block integrity checks, configurable environment-based deployment, and extensibility through module separation. The repository also includes documented improvements that address bugs, reduce code duplication, and improve maintainability.

Overall, the project provides an applied, code-backed implementation of decentralized secure data sharing, with domain adaptation toward healthcare records and optional AI inference capabilities.

# Abbreviations

- AES: Advanced Encryption Standard
- AI: Artificial Intelligence
- API: Application Programming Interface
- CID: Content Identifier
- CNN: Convolutional Neural Network
- CSRF: Cross-Site Request Forgery
- DICOM: Digital Imaging and Communications in Medicine
- HTTP: Hypertext Transfer Protocol
- IPFS: InterPlanetary File System
- JWT: JSON Web Token
- MB: Megabyte
- MRI: Magnetic Resonance Imaging
- PoW: Proof of Work
- RBAC: Role-Based Access Control
- SHA-256: Secure Hash Algorithm 256-bit
- SQL: Structured Query Language

# Chapter 1: Introduction

## 1.1 Background

Secure file sharing is a recurring challenge in distributed systems, especially when files are sensitive and access needs to be auditable. Traditional centralized file services simplify control but create concentrated trust and potential single points of failure. Decentralized architectures, especially when integrated with blockchain and content-addressable storage, attempt to improve transparency, resilience, and traceability.

This repository addresses that challenge through two related application contexts:
- A decentralized file sharing implementation with peer-aware blockchain synchronization.
- A healthcare extension that applies the same decentralized principles to medical image records and diagnosis-support workflows.

The healthcare application is implemented using Flask and a modular Python architecture. The implementation includes user accounts, role assignment, encrypted file processing, blockchain record insertion, and record retrieval under access checks. In addition, AI model integration is supported in a way that remains optional; if trained models are unavailable, the system still runs and can switch to simulation-style behavior.

The resulting software is not a single isolated script but a composed system where multiple concerns are explicitly separated:
- Encryption and storage operations in the data layer.
- Block and consensus operations in the blockchain layer.
- Authentication and permission mapping in access control.
- Inference and preprocessing logic in AI modules.
- Route orchestration in the Flask application.

## 1.2 Relevance

The project is relevant for both systems engineering and healthcare informatics for the following reasons:

1. It demonstrates how decentralized data references can coexist with application-level usability.
2. It treats privacy as an operational mechanism, not only as documentation, by encrypting file payloads before storage.
3. It introduces immutable, chronological recording of data events through blocks and hashes.
4. It applies role-based authorization to limit operations by actor type (patient, doctor, admin, researcher).
5. It provides an entry point for AI-assisted diagnosis workflows while keeping the rest of the platform functional without hard dependency on model availability.
6. It shows practical fallback strategy design (IPFS unavailable -> local storage handler) to preserve service continuity.

For educational and prototype-level deployments, this integration is important because it reflects real trade-offs: decentralization versus complexity, modularity versus coordination overhead, and security controls versus user experience friction.

## 1.3 Organization of the Report

This report is structured into nine chapters plus future scope and sample code section:

1. Chapter 1 introduces project background, relevance, and report flow.
2. Chapter 2 surveys related technical domains and frames the project problem.
3. Chapter 3 summarizes software and hardware requirements based on repository content.
4. Chapter 4 explains methodology, text-based project plan, and proposed approach.
5. Chapter 5 provides text-only analysis equivalent to use case/class/activity/sequence interpretation.
6. Chapter 6 provides text-only design discussion including data-flow levels and logic flow.
7. Chapter 7 describes implemented architecture and concrete module status.
8. Chapter 8 discusses result analysis grounded in available project evidence.
9. Chapter 9 concludes implementation outcomes and practical implications.

# Chapter 2: Literature Survey

## 2.1 Related Work

The implemented code reflects convergence of several established areas of work:

1. Blockchain-backed audit trails for high-integrity event recording.
2. IPFS-style content-addressable storage for decentralized file persistence.
3. Symmetric encryption for securing file payloads at rest and in transfer contexts.
4. Flask-based web systems for rapid prototyping of secure workflows.
5. AI image classification pipelines using transfer-learning-capable model families (for example MobileNet-oriented training scripts).

Rather than reproducing a formal bibliographic survey, the repository operationalizes these ideas through executable modules, scripts, and configuration conventions.

## 2.2 Basic Terminologies

The following terms are directly relevant to understanding this project:

1. Block: A structured unit in the chain containing index, timestamp, records, proof, and previous hash.
2. Genesis Block: The initial block that seeds chain state.
3. Proof of Work: A computational process used here to derive valid block proofs under a configured difficulty.
4. Hash: Deterministic digest used for block linking and file identification references.
5. IPFS Hash/CID: Content identifier returned for stored encrypted file content.
6. Access List: Record-level list of users permitted to access a stored item.
7. Role Permissions: Mapping from user role to allowed operations.
8. Consent: Healthcare-specific access gating concept; in code, consent manager integration is present.
9. Model Registry: Configuration map for selecting AI model files by record/profile aliases.
10. Fallback Storage Mode: Local storage operation used when IPFS connectivity/authentication is unavailable.

## 2.3 Existing System

Within this repository context, the "existing system" refers to conventional file sharing behavior and early monolithic implementations before improvements:

1. File sharing without decentralized audit can make event verification difficult.
2. Direct storage without encryption can expose data if storage endpoints are accessed.
3. Non-modular server logic tends to increase duplication and bug risk.
4. Insufficient role checks can blur boundaries between patient and clinician access.

The project documentation in the repository improvement summary also notes earlier maintenance concerns, such as duplicated code and socket handler issues, indicating practical evolution from less robust states.

## 2.4 Problem Statement

The key problem solved by this project can be expressed as follows:

Design and implement a decentralized, secure, and traceable file sharing platform where:
- file content confidentiality is preserved,
- file references are immutable and auditable,
- access is controlled by role and ownership logic,
- system operation remains resilient under partial infrastructure failure,
- and healthcare workflows can optionally include model-assisted diagnosis.

Constraints visible in implementation include file-size limits, allowed file formats, environment configuration requirements, and dependency-sensitive functionality (for example AI and external IPFS connectivity).

# Chapter 3: Requirement Gathering

## 3.1 Software Requirements

The repository and requirements files indicate the following software requirements:

1. Python runtime environment capable of running Flask applications and training scripts.
2. Flask and related middleware:
   - Flask
   - Flask-WTF
   - Werkzeug
3. Environment/configuration tooling:
   - python-dotenv
4. Cryptography libraries:
   - pycryptodome
   - pyAesCrypt
5. File and image handling:
   - Pillow
6. Networking and HTTP integration:
   - requests
7. Dataset acquisition for training scripts:
   - kagglehub
8. Optional AI stack (as commented optional dependency in requirements):
   - TensorFlow
   - NumPy
9. SQLite storage usage for user/auth related records (inferred from configured URI and db initialization patterns).

Additional logical software requirements from source behavior:

1. Environment variable support for secrets and model mapping.
2. Write permissions on upload, download, and data state directories.
3. Browser compatibility for form-based flows in Flask templates.

If a required external service is unavailable, the healthcare application demonstrates a local storage fallback path, reducing strict dependency lock on IPFS availability.

## 3.2 Hardware Requirements

Exact hardware specs are not explicitly defined in the repository. Based on implementation behavior and dependencies, practical minimum hardware considerations are:

1. CPU sufficient for Flask server execution and PoW loop processing.
2. RAM sufficient for web app runtime, file encryption/decryption buffers, and optional inference operations.
3. Disk storage for uploads, downloads, blockchain state, local IPFS fallback directory, and model artifacts.
4. Network connectivity for external IPFS service interaction and dataset download workflows.
5. For model training scripts, higher CPU/GPU and memory are beneficial but not mandatory for application startup.

No formal benchmark sheet is present; therefore exact numeric hardware thresholds are not implemented yet.

# Chapter 4: Plan of Project

## 4.1 Methodology

The implemented methodology can be summarized in sequential engineering layers:

1. User and role initialization:
   - Registration and login routes create authenticated sessions.
   - Role values map to permission sets through RBAC definitions.

2. Secure file intake:
   - Uploaded files are validated against allowed extensions and size constraints.
   - Files are encrypted before being passed to distributed or local content storage.

3. Storage and content addressing:
   - Primary strategy uses IPFS handler integration.
   - On connectivity/authentication failure, local storage handler is used as fallback.

4. Immutable metadata recording:
   - A medical record object including patient ID, uploader ID, content hash, type, and metadata is added.
   - New blocks are mined using proof-of-work and linked to previous block hash.

5. Access governance:
   - Access checks combine ownership and role logic.
   - Additional consent-aware checks are applied for clinician/researcher contexts in runtime policy logic.

6. Retrieval and diagnosis:
   - Authorized users can retrieve records and decrypt content.
   - Diagnosis route logic can select trained model by profile/type aliases or use simulation fallback.

7. Synchronization and continuity:
   - Blockchain includes node set management and chain replacement by longest valid chain policy.
   - Persistent state load/save mechanisms support continuity across process restarts.

## 4.2 Project Plan (TEXT ONLY, no Gantt)

A practical project execution plan, consistent with repository evolution, can be represented in text phases:

1. Phase 1 - Baseline decentralized sharing:
   - Implement block and chain structures.
   - Add PoW mechanism and chain validation.
   - Integrate file encryption and hash-based retrieval.

2. Phase 2 - Web workflow enablement:
   - Build Flask routes for upload, download, login, and dashboard views.
   - Add request validation and session handling.

3. Phase 3 - Access and security hardening:
   - Define role permissions.
   - Introduce grant/revoke pathways and ownership checks.
   - Add CSRF protection and secure filename handling.

4. Phase 4 - Healthcare adaptation:
   - Introduce patient-centric records and diagnosis metadata.
   - Add modular healthcare package structure.
   - Add consent-aware policy checks.

5. Phase 5 - AI extension:
   - Provide training scripts for medical imaging datasets.
   - Add model registry parsing and predictor dispatch.
   - Keep app operable when AI model files are absent.

6. Phase 6 - Code quality improvements:
   - Reduce duplicated utility logic.
   - Fix critical bugs and improve maintainability.

## 4.3 Proposed System (TEXT ONLY)

The proposed system, as realized in the repository, is a modular decentralized application architecture where:

1. The web tier handles user interaction and request orchestration.
2. The data layer secures files through encryption and handles storage backends.
3. The blockchain layer guarantees append-only record history and integrity verification.
4. The access control layer governs operation eligibility by role and policy.
5. The AI layer contributes optional diagnosis assistance for selected imaging categories.

Compared with a centralized single-database approach, this design prioritizes traceability and secure distribution, while intentionally retaining practical fallback behavior to prevent complete service interruption when one external service fails.

# Chapter 5: Project Analysis (TEXT ONLY)

## 5.1 Use Case Description

The implemented behavior supports the following major use-case families:

1. Account and session use cases:
   - User registers account with selected role.
   - User logs in and receives session context.
   - User logs out and session state is cleared.

2. Record lifecycle use cases:
   - Authorized user uploads medical image/file.
   - File is encrypted and stored; returned hash is recorded in blockchain.
   - User views records they are allowed to access.
   - User requests retrieval/download of accessible records.

3. Access management use cases:
   - Patient/uploader can grant access to other users.
   - Access can be revoked for one or more records.
   - Doctors/researchers are checked against consent-aware runtime policy.

4. Administrative/network use cases:
   - Admin-level capabilities include broader visibility and management actions per permission map.
   - Node list can be updated and chain synchronization can occur through consensus replacement.

5. Diagnosis use cases:
   - User triggers diagnosis for selected record.
   - System attempts model selection via profile/type keys.
   - If no model is loaded, simulated analysis path remains available.

## 5.2 Class Structure Explanation

Class-level organization visible from modules indicates clear domain separation:

1. Configuration classes:
   - `Config`, `DevelopmentConfig`, `ProductionConfig` encapsulate runtime options.

2. Blockchain classes:
   - `HealthcareBlockchain` manages chain state, pending records, PoW mining, validation, consensus, and access grant/revoke operations.
   - `Block` and `MedicalRecord` (imported into blockchain module) represent structural data entities for chain storage.

3. Access classes:
   - `Role` and `Permission` enums represent authorization vocabulary.
   - Role-permission mapping and helper functions provide deterministic policy checks.
   - `User` and auth manager constructs are imported and used in app-level session logic.

4. Data layer classes:
   - AES cipher abstraction for encryption/decryption.
   - Storage handlers for IPFS and local fallback.
   - File handler for upload/download path handling and processing.

5. AI classes:
   - `DiseasePredictor` for loading models and inference behavior.
   - `ImagePreprocessor` for input shaping prior to prediction.

6. Consent integration:
   - `ConsentManager` is instantiated and used for clinician/researcher access checks.

The class structure demonstrates high cohesion within modules and lower coupling across them through imported interfaces rather than deeply shared global state.

## 5.3 Activity Flow Explanation

A text-based activity flow for core upload-to-record operation:

1. User submits upload request.
2. Server validates authentication and required form data.
3. File extension and constraints are validated.
4. File is encrypted via data layer utility.
5. Encrypted content is sent to storage handler (IPFS or local fallback).
6. Returned content hash/CID is captured.
7. Blockchain receives new medical record request.
8. Mining process creates/updates block with PoW-compliant proof.
9. Success response and dashboard/list updates are presented to user.

A text-based activity flow for record viewing:

1. User opens records page.
2. Server identifies role and user id from session.
3. Record set is filtered by policy checks and consent status.
4. View is rendered with accessible records only.

A text-based activity flow for diagnosis:

1. User invokes diagnosis on a record.
2. Candidate model keys are inferred from profile/type/filename metadata.
3. Matching loaded predictor is selected if available.
4. If model unavailable, simulation path is used.
5. Result/confidence metadata is produced and exposed in response context.

## 5.4 Sequence Flow Explanation

Textual sequence for secure retrieval:

1. Client requests a specific record by identifier/hash.
2. App retrieves current user from session.
3. Blockchain and policy layer verify that user can access the requested record.
4. Storage layer fetches encrypted payload by hash.
5. Decryption routine converts payload to usable file form.
6. Server returns file stream/response to client.

Textual sequence for chain replacement:

1. Node invokes chain replacement routine.
2. Local node iterates known peer nodes.
3. For each node, chain endpoint is queried with timeout.
4. Received chain is converted into block objects.
5. Chain validity check is applied using hash linkage and PoW verification.
6. Longest valid chain is selected and local chain is replaced if applicable.
7. Updated state is persisted.

# Chapter 6: Project Design (TEXT ONLY)

## 6.1 Data Flow Explanation

### 6.1.1 Level 0

At a high level, data flow can be described as interaction among four macro entities:

1. User interface layer (templates/routes) receives actions.
2. Application layer orchestrates auth, storage, blockchain, and AI services.
3. Storage layer persists encrypted file content (IPFS or local fallback).
4. Blockchain layer stores immutable metadata and access-related record details.

Input data (user credentials, file uploads, access actions) enters via HTTP routes. Output data includes rendered pages, JSON endpoints, file responses, and chain status information.

### 6.1.2 Level 1

A more detailed text-level data movement:

1. Registration/Login path:
   - Form input -> auth manager -> database persistence/check -> session variables -> dashboard redirect.

2. Upload path:
   - File input -> secure filename + validation -> temporary or managed path -> encryption -> storage upload -> content hash -> blockchain record insert -> block mining -> state save.

3. Record listing path:
   - Session user -> role and permission evaluation -> chain scan and filtering -> response render.

4. Access grant/revoke path:
   - Owner action -> target record resolution -> access list mutation in record object -> state save.

5. Diagnosis path:
   - Record/metadata -> model key inference -> predictor selection -> preprocessing -> prediction or simulation -> result output.

6. Chain API path:
   - Internal chain objects -> dictionary serialization -> JSON response for peer consensus checks.

## 6.2 Flow Logic Explanation

The control flow of the system follows a guarded pipeline style:

1. Every sensitive route begins with authentication and, where required, role/permission decorators.
2. Data operations are performed only after validation and policy checks pass.
3. Storage operations are abstracted behind handlers, allowing backend substitution without major route rewriting.
4. Blockchain state operations include persistence hooks to maintain durable history.
5. Consensus checks are defensive with timeout handling and invalid-node skipping behavior.
6. AI logic is optional-path enabled, avoiding hard crashes in environments without trained model assets.

This flow logic makes the application robust under heterogeneous runtime conditions while preserving a clear security-first ordering.

# Chapter 7: Implemented System

## 7.1 System Architecture

Implemented architecture in this repository includes the following concrete components:

1. Top-level decentralized sharing subsystem:
   - `main_server` and `client_server_1` server variants with blockchain and file sharing logic.
   - Shared utility module (`shared_utils.py`) introduced to reduce duplication.

2. Healthcare subsystem (`healthcare_blockchain`):
   - `app.py` Flask application integrating all layers.
   - `modules/data_layer` for encryption, file handling, and storage handlers.
   - `modules/blockchain` for block chain structures and consensus behavior.
   - `modules/access_control` for authentication and RBAC definitions.
   - `modules/ai_layer` for preprocessing and diagnosis.
   - `modules/consent` package present and integrated through `ConsentManager` imports in app-level flow.

3. Training and model support:
   - Separate training scripts for different imaging datasets.
   - Configurable model registry through environment variable mapping.

4. Static/template assets:
   - HTML templates and static resources support web interaction flow.

5. Persistence:
   - Blockchain state JSON in data directory.
   - SQLite database for user/auth/consent-related operations.

## 7.2 Implementation Details

### Completed Modules

Based on available files and code wiring, the following modules are implemented:

1. User authentication and session flows (register, login, logout).
2. Role and permission definitions with helper checks.
3. File upload and download workflows with extension constraints.
4. AES-based encryption/decryption integration in data handling path.
5. IPFS storage handler with connectivity test and local fallback behavior.
6. Blockchain record insertion, PoW mining, chain validation, and serialization.
7. Chain consensus replacement using longest-valid-chain logic.
8. Access grant/revoke methods for record-level and patient-level scopes.
9. Records retrieval filtered through policy checks.
10. AI predictor loading and model-key routing logic.
11. Dataset-specific model training scripts for multiple imaging categories.
12. Security hardening items documented in repository improvement notes (CSRF, configuration cleanup, bug fixes).

### Modules In Progress

From available project materials, the following appear partially implemented or evolving:

1. Consent subsystem internals: package is present and imported, but detailed manager implementation file was not visible in current directory listing snapshot.
2. Expanded production-grade observability: logging and advanced monitoring are not comprehensively documented as finalized.
3. Broader automated test coverage inside healthcare package: tests directory exists, but complete suite breadth is not fully evidenced from currently reviewed files.

### Not Implemented Yet

1. Formal references section in project report context: Not implemented yet.
2. Diagram assets in this generated report: intentionally not implemented, as required.
3. Hyperledger/FOLS/federated-learning/mobile/multi-hospital upgrades listed as future checkboxes in documentation: Not implemented yet.
4. Exact hardware benchmark specification document: Not implemented yet.

# Chapter 8: Result Analysis

The project contains both implementation evidence and a documented improvement log. From these sources, results can be analyzed on three axes.

1. Functional result:
   - The application supports complete user-facing flows for account management, secure file intake, record storage, and retrieval with access checks.
   - Blockchain chain state can be exposed and validated, enabling integrity-focused operations.
   - Optional AI workflows are integrated in a non-blocking manner.

2. Security and control result:
   - Files are encrypted prior to storage, reducing direct exposure from content-addressed retrieval alone.
   - Role-permission mapping and session guards improve least-privilege behavior.
   - CSRF and secure filename handling are integrated in server-side flow.
   - Access list + consent-aware checks create additional control boundaries for clinical access.

3. Engineering quality result:
   - Improvement notes indicate remediation of critical defects and reduction of duplicated server logic.
   - Shared utility extraction and cleanup actions improve maintainability and consistency.
   - Local fallback strategy for IPFS improves operational resilience during dependency failures.

Limitations observed in current state:

1. Some advanced features are declared as future upgrades rather than completed modules.
2. Detailed production metrics (latency, throughput, large-scale peer behavior) are not presented as formal benchmark outputs.
3. Full internal visibility into all consent module internals was not available from reviewed directory snapshot.

Overall result interpretation: the codebase has moved beyond conceptual prototype into a functional modular system, with clear evidence of iterative hardening and extensibility.

# Chapter 9: Conclusion

This project successfully demonstrates a decentralized secure data sharing approach with healthcare-focused adaptation. The implementation combines encryption, distributed storage references, blockchain-backed integrity, role-based policy checks, and optional AI diagnosis support within a single Flask-based platform.

The architecture balances ambition and practicality. It does not depend on only one backend mode, because storage fallback behavior is implemented. It does not fail entirely when trained AI models are absent, because diagnosis logic can degrade gracefully. It does not leave access to implicit trust, because role and policy checks are integrated at runtime.

From a software engineering standpoint, the repository also reflects active maintenance: bug fixes, deduplication, and clearer modular boundaries are already documented and applied. This is an important indicator of project maturity relative to one-time demonstration code.

In conclusion, the implemented system provides a technically coherent foundation for secure decentralized record workflows and can be extended toward stronger healthcare-grade deployment controls in subsequent iterations.

# Future Scope

The following future directions are either explicitly listed in project documentation or logically aligned with current architecture:

1. Upgrade blockchain framework choices for enterprise-scale deployment scenarios.
2. Add advanced encryption research pathways where feasible.
3. Expand federated or privacy-preserving AI training workflows.
4. Extend client channels to mobile applications.
5. Enable broader multi-organization healthcare network participation.
6. Increase automated testing depth, especially around consent and policy edge cases.
7. Add richer operational telemetry, structured logging, and failure analytics.

# Sample Code

```python
# From healthcare_blockchain/modules/blockchain/blockchain.py

def proof_of_work(self, previous_proof: int) -> int:
    """
    Simple Proof of Work algorithm.

    Args:
        previous_proof: Proof from the previous block

    Returns:
        New proof that satisfies difficulty requirement
    """
    new_proof = 1
    while True:
        hash_operation = hashlib.sha256(
            str(new_proof ** 2 - previous_proof ** 2).encode()
        ).hexdigest()

        if hash_operation[:self.difficulty] == '0' * self.difficulty:
            return new_proof
        new_proof += 1
```

```python
# From healthcare_blockchain/app.py (model registry parsing)

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
```
