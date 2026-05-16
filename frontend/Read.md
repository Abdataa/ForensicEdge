## Architecture decisions
for the frontend of this project Pages Router is selected as architecture .

** Pages Router (not App Router)— uses pages/ directory which is simpler better, documented, and works cleanly with _app.tsx for global providers.App Router adds complexity that isn't needed for this project scope **

## Folder Structure of the frontend
frontend/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── postcss.config.js
│
├── src/
│   ├── styles/globals.css
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── authService.ts
│   │   ├── imageService.ts
│   │   ├── compareService.ts
│   │   ├── reportService.ts
│   │   └── feedbackService.ts
│   │
│   ├── context/AuthContext.tsx
│   ├── hooks/useAuth.ts
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Spinner.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Modal.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── AppLayout.tsx
│   │   └── forensic/
│   │       ├── EvidenceTypeSelector.tsx
│   │       ├── ImageUploader.tsx
│   │       ├── SimilarityResultCard.tsx
│   │       ├── ReportViewer.tsx
│   │       └── FeedbackForm.tsx
│   │
│   └── pages/
│       ├── _app.tsx
│       ├── index.tsx
│       ├── login.tsx
│       ├── dashboard.tsx
│       ├── upload.tsx
│       ├── compare.tsx
│       ├── reports.tsx
│       ├── logs.tsx
│       ├── feedback.tsx
│       ├── admin.tsx
│       └── change-password.tsx
|       └──cases.tsx


## Run with

cd frontend
npm install
npm run dev
## Backend
📁 ForensicEdge/
│
├── 📄 README.md
├── 📄 .gitignore
├── 📄 docker-compose.yml
├── 📄 LICENSE
│
├── 📁 backend/
│   .env
│   .gitignore
│   alembic.ini
│   project_structure.txt
│   requirements.txt
│   seed_data.py
│   test_db.py
│
├───alembic
│   │   env.py
│   │   README
│   │   script.py.mako
│   │
│   └───versions
│           01cc3e270e2b_initial_postgresql_schema.py
│           5aa38828c404_initial_migration.py
│
└───app
    │   main.py
    │
    ├───api
    │   │   routes_admin.py
    │   │   routes_auth.py
    │   │   routes_cases.py
    │   │   routes_compare.py
    │   │   routes_feedback.py
    │   │   routes_logs.py
    │   │   routes_ml.py
    │   │   routes_report.py
    │   │   routes_upload.py
    │   │   temp_routes_upload.py
    │   │
    │   └───__pycache__
    │           routes_admin.cpython-311.pyc
    │           routes_auth.cpython-311.pyc
    │           routes_cases.cpython-311.pyc
    │           routes_compare.cpython-311.pyc
    │           routes_feedback.cpython-311.pyc
    │           routes_logs.cpython-311.pyc
    │           routes_ml.cpython-311.pyc
    │           routes_report.cpython-311.pyc
    │           routes_upload.cpython-311.pyc
    │           __init__.cpython-311.pyc
    │
    ├───core
    │   │   config.py
    │   │   database.py
    │   │   dependencies.py
    │   │   dependencies_ml_addition.py
    │   │   security.py
    │   │
    │   └───__pycache__
    │           config.cpython-311.pyc
    │           database.cpython-311.pyc
    │           dependencies.cpython-311.pyc
    │           security.cpython-311.pyc
    │
    ├───db
    │   │   base.py
    │   │   session.py
    │   │
    │   └───__pycache__
    │           base.cpython-311.pyc
    │
    ├───models
    │   │   audit_log.py
    │   │   case.py
    │   │   dataset.py
    │   │   feedback.py
    │   │   forensic_image.py
    │   │   ml.py
    │   │   report.py
    │   │   similarity_result.py
    │   │   user.py
    │   │
    │   └───__pycache__
    │           audit_log.cpython-311.pyc
    │           case.cpython-311.pyc
    │           dataset.cpython-311.pyc
    │           feedback.cpython-311.pyc
    │           forensic_image.cpython-311.pyc
    │           ml.cpython-311.pyc
    │           report.cpython-311.pyc
    │           similarity_result.cpython-311.pyc
    │           user.cpython-311.pyc
    │
    ├───schemas
    │   │   case_schema.py
    │   │   feedback_schema.py
    │   │   image_schema.py
    │   │   ml_schema.py
    │   │   report_schema.py
    │   │   similarity_schema.py
    │   │   user_schema.py
    │   │
    │   ├───audit
    │   │   │   auth_events.py
    │   │   │   case_events.py
    │   │   │   image_events.py
    │   │   │   registry.py
    │   │   │   report_events.py
    │   │   │   __init__.py
    │   │   │
    │   │   └───__pycache__
    │   │           auth_events.cpython-311.pyc
    │   │           case_events.cpython-311.pyc
    │   │           image_events.cpython-311.pyc
    │   │           registry.cpython-311.pyc
    │   │           report_events.cpython-311.pyc
    │   │           __init__.cpython-311.pyc
    │   │
    │   └───__pycache__
    │           case_schema.cpython-311.pyc
    │           feedback_schema.cpython-311.pyc
    │           image_schema.cpython-311.pyc
    │           ml_schema.cpython-311.pyc
    │           report_schema.cpython-311.pyc
    │           similarity_schema.cpython-311.pyc
    │           user_schema.cpython-311.pyc
    │
    ├───services
    │   │   auth_service.py
    │   │   case_service.py
    │   │   feedback_service.py
    │   │   image_service.py
    │   │   log_service.py
    │   │   ml_service.py
    │   │   report_service.py
    │   │   similarity_service.py
    │   │   similarity_service_additions.py
    │   │
    │   └───__pycache__
    │           auth_service.cpython-311.pyc
    │           case_service.cpython-311.pyc
    │           feedback_service.cpython-311.pyc
    │           image_service.cpython-311.pyc
    │           log_service.cpython-311.pyc
    │           ml_service.cpython-311.pyc
    │           report_service.cpython-311.pyc
    │           similarity_service.cpython-311.pyc
    │
    ├───utils
    │   │   file_validator.py
    │   │   image_processing.py
    │   │   logger.py
    │   │
    │   └───__pycache__
    │           logger.cpython-311.pyc
    │
    └───__pycache__
            main.cpython-311.pyc
├── 📁 ai_engine/ # AI & Research Layer
│   ├── 📄 requirements.txt
│   ├── 📄 config.py
│   │
│   ├── 📁 datasets/
│   │   ├── 📁 raw/
│   │   │   ├── fingerprints/SOCOFing/
│   │   │   │                         ├──Real/
│   │   │   │                         └──Altered/
│   │   │   └── toolmarks/
│   │   ├──📁 processed/
│   │   ├── 📁 processed_clean/
│   │   └── 📁 feedback_samples/#Hard examples for
│   │                            #retraining
│   ├── 📁 preprocessing/
│   │   ├── 📄 augment.py
│   │   ├── 📄 enhance.py
│   │   └── 📄 normalize.py
│   │
│   ├── 📁 models/
│   │   ├── 📄 cnn_feature_extractor.py
│   │   ├── 📄 siamese_network.py
│   │   ├── 📄 loss_functions.py
│   │   ├
│   │   └── 📁 weights/ # Ignored in git
│   │        ├───fingerprint
│   │        │       └──best_model.pth
│   │        └───toolmark #best_model of the tool mark
│   │
│   ├── 📁 training/
│   │   ├── 📄 train_siamese.py
│   │   ├── 📄 evaluate.py
│   │   ├── 📄 metrics.py
│   │   ├── 📄 siamese_dataset.py
│   │   │
│   │   └── 📁 experiments/# Research Experiments
│   │       ├── 📄 baseline_experiment.py
│   │       ├── 📄 augmentation_experiment.py
│   │       └── 📄 threshold_experiment.py
│   │
│   └── 📁 inference/
│       ├── 📄 preprocess.py
│       ├── 📄 feature_extractor.py
│       ├── 📄 compare.py
│       └── inference.md
│
│
├── 📁 frontend/                         # Presentation Layer
│   ├── 📄 package.json
│   ├── 📄 next.config.js
│   │
│   ├── 📁 public/
│   │
│   └── 📁 src/
│       ├── 📁 pages/
│       │   ├── 📄 index.tsx
│       │   ├── 📄 login.tsx
│       │   ├── 📄 register.tsx
│       │   ├── 📄 dashboard.tsx
│       │   ├── 📄 upload.tsx
│       │   ├── 📄 compare.tsx
│       │   ├── 📄 reports.tsx
│       │   ├── 📄 admin.tsx
│       │   └── 📄 feedback.tsx
│       │
│       ├── 📁 components/
│       │   ├── 📄 Navbar.tsx
│       │   ├── 📄 Sidebar.tsx
│       │   ├── 📄 ImageUploader.tsx
│       │   ├── 📄 SimilarityResultCard.tsx
│       │   ├── 📄 ReportViewer.tsx
│       │   ├── 📄 FeedbackForm.tsx
│       │   └── 📄 ProtectedRoute.tsx
│       │
│       ├── 📁 services/
│       │   ├── 📄 api.ts
│       │   ├── 📄 authService.ts
│       │   ├── 📄 imageService.ts
│       │   ├── 📄 reportService.ts
│       │   └── 📄 feedbackService.ts
│       │
│       ├── 📁 context/
│       │   └── 📄 AuthContext.tsx
│       │
│       └── 📁 styles/
│           └── 📄 globals.css
│
│
├── 📁 storage/                          # Runtime Generated Files
│   ├── 📁 uploads/
│   ├── 📁 reports/
│   └── 📁 logs/
│
│
├── 📁 database/                         # Dev Database + Migrations
│   ├── forensic_edge.db
│   └── 📁 migrations/
│
│
├── 📁 tests/
│   ├── 📁 backend/
│   ├── 📁 ai_engine/
│   └── 📁 integration/
│
│
├── 📁 docs/
│   ├── 📄 API_Documentation.md
│   ├── 📄 System_Architecture.png
│   ├── 📁 UML_Diagrams/
│   ├── 📄 Experiment_Results.pdf
│   └── 📄
