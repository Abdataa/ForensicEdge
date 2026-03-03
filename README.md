# ForensicEdge

AI-Optimized Evidence Analysis System for Fingerprint and Toolmark Comparison.

## Core Technologies
- PyTorch (CNN + Siamese Network)
- FastAPI Backend
- React Frontend
- OpenCV Image Processing

## Architecture
- AI Engine (Feature Extraction + Similarity)
- Backend API Layer
- Interactive Dashboard
- Secure Storage

## Features
- Fingerprint Similarity Matching
- Toolmark Comparison
- AI-Based Feature Extraction
- Forensic Report Generation

## Status
Under Active Development (Senior Project - ASTU)

📁 ForensicEdge/
│
├── 📄 README.md
├── 📄 .gitignore
├── 📄 docker-compose.yml
├── 📄 LICENSE
│
├── 📁 backend/                          # FastAPI Application Layer
│   ├── 📄 requirements.txt
│   ├── 📄 Dockerfile
│   ├── 📄 .env
│   │
│   └── 📁 app/
│       ├── 📄 main.py
│       │
│       ├── 📁 api/                      # Route Definitions
│       │   ├── 📄 routes_auth.py
│       │   ├── 📄 routes_upload.py
│       │   ├── 📄 routes_compare.py
│       │   ├── 📄 routes_report.py
│       │   ├── 📄 routes_admin.py
│       │   ├── 📄 routes_logs.py
│       │   └── 📄 routes_feedback.py
│       │
│       ├── 📁 core/                     # Core Configurations
│       │   ├── 📄 config.py
│       │   ├── 📄 security.py
│       │   ├── 📄 database.py
│       │   └── 📄 dependencies.py
│       │
│       ├── 📁 models/                   # SQLAlchemy Models
│       │   ├── 📄 user.py
│       │   ├── 📄 forensic_image.py
│       │   ├── 📄 similarity_result.py
│       │   ├── 📄 report.py
│       │   ├── 📄 dataset.py
│       │   ├── 📄 audit_log.py
│       │   └── 📄 feedback.py
│       │
│       ├── 📁 schemas/                  # Pydantic Schemas
│       │   ├── 📄 user_schema.py
│       │   ├── 📄 image_schema.py
│       │   ├── 📄 similarity_schema.py
│       │   ├── 📄 report_schema.py
│       │   └── 📄 feedback_schema.py
│       │
│       ├── 📁 services/                 # Business Logic Layer
│       │   ├── 📄 auth_service.py
│       │   ├── 📄 image_service.py
│       │   ├── 📄 similarity_service.py
│       │   ├── 📄 report_service.py
│       │   ├── 📄 log_service.py
│       │   └── 📄 feedback_service.py
│       │
│       ├── 📁 db/
│       │   ├── 📄 base.py
│       │   └── 📄 session.py
│       │
│       └── 📁 utils/
│           ├── 📄 file_validator.py
│           ├── 📄 image_processing.py
│           └── 📄 logger.py
│
│
├── 📁 ai_engine/                        # AI & Research Layer (Your Domain)
│   ├── 📄 requirements.txt
│   ├── 📄 config.py
│   │
│   ├── 📁 datasets/
│   │   ├── 📁 raw/
│   │   │   ├── fingerprints/
│   │   │   └── toolmarks/
│   │   │
│   │   ├── 📁 processed/
│   │   └── 📁 feedback_samples/         # Hard examples for retraining
│   │
│   ├── 📁 preprocessing/
│   │   ├── 📄 augment.py
│   │   ├── 📄 enhance.py
│   │   └── 📄 normalize.py
│   │
│   ├── 📁 models/
│   │   ├── 📄 cnn_feature_extractor.py
│   │   ├── 📄 siamese_network.py
│   │   ├── 📄 loss_functions.py
│   │   ├── 📄 model_loader.py
│   │   └── 📁 weights/                  # Ignored in git
│   │
│   ├── 📁 training/
│   │   ├── 📄 train.py
│   │   ├── 📄 evaluate.py
│   │   ├── 📄 metrics.py
│   │   ├── 📄 retrain_from_feedback.py
│   │   │
│   │   └── 📁 experiments/              # Research Experiments
│   │       ├── 📄 baseline_experiment.py
│   │       ├── 📄 augmentation_experiment.py
│   │       └── 📄 threshold_experiment.py
│   │
│   └── 📁 inference/
│       ├── 📄 preprocess.py
│       ├── 📄 feature_extractor.py
│       └── 📄 compare.py
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