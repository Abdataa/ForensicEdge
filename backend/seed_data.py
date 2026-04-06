# backend/seed_data.py
"""
Database Seeding Script for ForensicEdge
Simplified - Only ONE Admin, NO Super Admin
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import uuid
import random
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.user import User
from models.forensic_image import ForensicImage
from models.forensic_image import ImageType
from models.preprocessed_image import PreprocessedImage
from models.feature_set import FeatureSet
from models.feedback import Feedback
from models.similarity_result import SimilarityResult
from models.report import Report
from models.audit_log import AuditLog
from models.ai_model import AIModel
from models.dataset import Dataset
from models.model_version import ModelVersion
from models.case import Case
from models.case_evidence import CaseEvidence

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# ============================================
# SAMPLE DATA GENERATION FUNCTIONS
# ============================================

def generate_sample_feature_vector():
    """Generate a random 64-dim feature vector"""
    return [random.uniform(0, 1) for _ in range(64)]

def generate_sample_minutiae():
    """Generate sample fingerprint minutiae points"""
    minutiae_types = ['ridge_ending', 'bifurcation', 'dot', 'island']
    return [
        {
            "type": random.choice(minutiae_types),
            "x": random.randint(0, 300),
            "y": random.randint(0, 300),
            "angle": random.uniform(0, 360),
            "quality": random.uniform(0.5, 1.0)
        }
        for _ in range(random.randint(10, 25))
    ]

def generate_sample_striations():
    """Generate sample toolmark striations"""
    return [
        {
            "start_x": random.randint(0, 200),
            "start_y": random.randint(0, 200),
            "end_x": random.randint(200, 400),
            "end_y": random.randint(200, 400),
            "width": random.uniform(0.5, 2.0),
            "depth": random.uniform(0.1, 0.5)
        }
        for _ in range(random.randint(5, 15))
    ]

# ============================================
# MAIN SEEDING FUNCTION
# ============================================

def seed_database():
    """Populate database with sample data"""
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print(" FORENSICEDGE DATABASE SEEDING")
        print("=" * 70)
        
        # ============================================
        # 1. CREATE USERS
        # ============================================
        print("\n 1. Creating Users...")
        
        # ONE Admin (System Administrator)
        admin = User(
            id=uuid.uuid4(),
            full_name="Abdi Dawud",
            email="abdi@forensicedge.com",
            password_hash=get_password_hash("Admin@123"),
            role="admin",
            is_active=True,
            badge_number="ADMIN001",
            department="System Administration",
            created_at=datetime.now()
        )
        db.add(admin)
        db.flush()
        print(f"   ✓ Created Admin: {admin.email} (System Administrator)")
        
        # AI Engineer
        ai_engineer = User(
            id=uuid.uuid4(),
            full_name="Abdullah Omar",
            email="abdullah@forensicedge.com",
            password_hash=get_password_hash("AIEngineer@123"),
            role="ai_engineer",
            is_active=True,
            badge_number="AI001",
            department="AI Research Lab",
            created_by=admin.id,
            created_at=datetime.now()
        )
        db.add(ai_engineer)
        db.flush()
        print(f"   ✓ Created AI Engineer: {ai_engineer.email}")
        
        # Analysts (Multiple)
        analysts = [
            {
                "name": "Meron Tilahun",
                "email": "meron@forensicedge.com",
                "badge": "ANL001",
                "dept": "Fingerprint Analysis Unit"
            },
            {
                "name": "Meti Jemal",
                "email": "meti@forensicedge.com",
                "badge": "ANL002",
                "dept": "Toolmark Analysis Unit"
            },
            {
                "name": "Abebe Kumbi",
                "email": "abebe@forensicedge.com",
                "badge": "ANL003",
                "dept": "Latent Print Unit"
            }
        ]
        
        analyst_users = []
        for data in analysts:
            analyst = User(
                id=uuid.uuid4(),
                full_name=data["name"],
                email=data["email"],
                password_hash=get_password_hash("Analyst@123"),
                role="analyst",
                is_active=True,
                badge_number=data["badge"],
                department=data["dept"],
                created_by=admin.id,
                created_at=datetime.now()
            )
            db.add(analyst)
            analyst_users.append(analyst)
            print(f"   ✓ Created Analyst: {analyst.email}")
        
        db.flush()
        
        # ============================================
        # 2. CREATE DATASETS
        # ============================================
        print("\n 2. Creating Datasets...")
        
        datasets = [
            {
                "name": "FVC2004 Fingerprint Dataset",
                "description": "Fingerprint Verification Competition 2004 dataset",
                "dataset_type": "fingerprint",
                "source": "FVC2004",
                "file_count": 5120,
                "size_mb": 245.6,
                "train_count": 4096,
                "val_count": 512,
                "test_count": 512
            },
            {
                "name": "NIST SD27 Fingerprint Dataset",
                "description": "NIST Special Database 27 - Fingerprint Minutiae",
                "dataset_type": "fingerprint",
                "source": "NIST",
                "file_count": 2580,
                "size_mb": 128.3,
                "train_count": 2064,
                "val_count": 258,
                "test_count": 258
            },
            {
                "name": "Toolmark Database v1",
                "description": "Toolmark striation patterns dataset",
                "dataset_type": "toolmark",
                "source": "Research Lab",
                "file_count": 1500,
                "size_mb": 89.4,
                "train_count": 1200,
                "val_count": 150,
                "test_count": 150
            }
        ]
        
        dataset_objects = []
        for data in datasets:
            dataset = Dataset(
                id=uuid.uuid4(),
                name=data["name"],
                description=data["description"],
                dataset_path=f"/data/datasets/{data['name'].replace(' ', '_')}.zip",
                dataset_type=data["dataset_type"],
                source=data["source"],
                file_count=data["file_count"],
                size_mb=data["size_mb"],
                train_count=data["train_count"],
                val_count=data["val_count"],
                test_count=data["test_count"],
                uploaded_by=ai_engineer.id,
                is_public=True,
                dataset_metadata={
                    "format": "TIFF",
                    "resolution": "500 DPI",
                    "year": 2024
                },
                created_at=datetime.now()
            )
            db.add(dataset)
            dataset_objects.append(dataset)
            print(f"   ✓ Created Dataset: {dataset.name}")
        
        db.flush()
        
        # ============================================
        # 3. CREATE MODEL VERSIONS
        # ============================================
        print("\n🤖 3. Creating Model Versions...")
        
        models = [
            {
                "name": "ForensicEdge CNN",
                "version": "1.0.0",
                "accuracy": 0.942,
                "loss": 0.234,
                "precision": 0.935,
                "recall": 0.951,
                "f1_score": 0.943,
                "false_match_rate": 0.005,
                "false_non_match_rate": 0.008,
                "status": "trained"
            },
            {
                "name": "ForensicEdge Siamese",
                "version": "2.0.0",
                "accuracy": 0.967,
                "loss": 0.156,
                "precision": 0.961,
                "recall": 0.973,
                "f1_score": 0.967,
                "false_match_rate": 0.003,
                "false_non_match_rate": 0.004,
                "status": "deployed"  # This is the active model
            },
            {
                "name": "ForensicEdge v3",
                "version": "3.0.0-beta",
                "accuracy": 0.981,
                "loss": 0.089,
                "precision": 0.978,
                "recall": 0.984,
                "f1_score": 0.981,
                "false_match_rate": 0.001,
                "false_non_match_rate": 0.002,
                "status": "training"
            }
        ]
        print("\n🤖 3. Creating AI Models...")

        ai_models = []

        model_data = [
        {"name": "ForensicEdge CNN", "version": "1.0.0"},
        {"name": "ForensicEdge Siamese", "version": "2.0.0"},
        {"name": "ForensicEdge v3", "version": "3.0.0-beta"}
]
        for data in model_data:
         model = AIModel(
          id=uuid.uuid4(),
          name=data["name"],
          version=data["version"],
          description=f"{data['name']} base model",
          model_path=f"/models/{data['name'].replace(' ', '_')}.pt",
          trained_by=ai_engineer.id,
          training_dataset_id=dataset_objects[0].id,
          status="training"
    )
        db.add(model)
        ai_models.append(model)

        db.flush()  # VERY IMPORTANT to generate IDs
        

        for model in ai_models:
         print(f"   ✓ Created AI Model: {model.name}")
        
        model_objects = []
        for i, data in enumerate(models):
            model = ModelVersion(
                model_id=ai_models[i % len(ai_models)].id,
                name=data["name"],
                version=data["version"],
                accuracy=data["accuracy"],
                loss=data["loss"],
                precision=data["precision"],
                recall=data["recall"],
                f1_score=data["f1_score"],
                false_match_rate=data["false_match_rate"],
                false_non_match_rate=data["false_non_match_rate"],
                model_path=f"/models/{data['name'].replace(' ', '_')}_{data['version']}.pt",
                training_dataset_id = dataset_objects[i % len(dataset_objects)].id,
                trained_by=ai_engineer.id,
                training_duration=random.uniform(3600, 14400),
                training_parameters={
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "epochs": 50,
                    "optimizer": "Adam",
                    "loss_function": "ContrastiveLoss"
                },
                is_active=(data["status"] == "deployed"),
                status=data["status"],
                created_on=datetime.now() - timedelta(days=30 - i*10),
                deployed_at=datetime.now() - timedelta(days=20 - i*10) if data["status"] == "deployed" else None
            )
            db.add(model)
            model_objects.append(model)
            print(f"   ✓ Created Model: {model.name} v{model.version} (Accuracy: {model.accuracy*100:.1f}%)")
        
        db.flush()
        
        # ============================================
        # 4. CREATE FORENSIC IMAGES
        # ============================================
        print("\n 4. Creating Forensic Images...")
        
        forensic_images = []
        
        # Create fingerprint images
        for i in range(15):
            analyst = random.choice(analyst_users)
            img = ForensicImage(
                id=uuid.uuid4(),
                user_id=analyst.id,
                image_type=ImageType.fingerprint.value,
                filename=f"sample_fingerprint_{i+1}.png",
                created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                file_path=f"/uploads/fingerprints/sample_fingerprint_{i+1}.png",
                original_filename=f"latent_print_{i+1}.png",
                file_size=random.randint(500000, 2000000),
                mime_type="image/png",
                status=random.choice(["uploaded", "preprocessed", "analyzed"]),
                description=f"Sample fingerprint #{i+1} from crime scene",
                tags=["latent", "crime_scene", f"case_{random.randint(1, 5)}"],
                metadata={
                    "scanner_model": "Cognitec 3D",
                    "resolution": "1000 DPI",
                    "acquisition_date": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
                }
            )
            db.add(img)
            forensic_images.append(img)
            print(f"   ✓ Created Fingerprint Image: {img.original_filename}")
        
        # Create toolmark images
        for i in range(10):
            analyst = random.choice(analyst_users)
            img = ForensicImage(
                id=uuid.uuid4(),
                user_id=analyst.id,
                filename=f"sample_toolmark_{i}.png",
                image_type=ImageType.toolmark.value,
                created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                file_path=f"/uploads/toolmarks/sample_toolmark_{i+1}.png",
                original_filename=f"toolmark_evidence_{i+1}.png",
                file_size=random.randint(300000, 1500000),
                mime_type="image/png",
                status=random.choice(["uploaded", "preprocessed", "analyzed"]),
                description=f"Sample toolmark #{i+1} from burglary scene",
                tags=["toolmark", "screwdriver", f"case_{random.randint(1, 5)}"],
                metadata={
                    "microscope": "Leica DM6000",
                    "magnification": "50x",
                    "material": "metal"
                }
            )
            db.add(img)
            forensic_images.append(img)
            print(f"   ✓ Created Toolmark Image: {img.original_filename}")
        
        db.flush()
        
        # ============================================
        # 5. CREATE PREPROCESSED IMAGES
        # ============================================
        print("\n 5. Creating Preprocessed Images...")
        
        preprocessed_images = []
        for img in forensic_images[:20]:
            filename = f"{img.original_filename.split('.')[0]}_enhanced.png"
            preprocessed = PreprocessedImage(
                id=uuid.uuid4(),
                original_image_id=img.id,
                processed_filename=filename,
                processed_path=f"/preprocessed/{img.original_filename.replace('.png', '_enhanced.png')}",
                enhancement_techniques=["grayscale", "noise_reduction", "contrast_enhancement", "ridge_enhancement"],
                user_id=img.user_id,
                quality_score=random.uniform(0.7, 0.98),
                processing_time=random.uniform(0.5, 2.5),
                created_at=img.created_at + timedelta(seconds=random.randint(10, 60))
            )
            db.add(preprocessed)
            preprocessed_images.append(preprocessed)
            print(f"   ✓ Preprocessed: {img.original_filename} (Quality: {preprocessed.quality_score:.2f})")
        
        db.flush()
        
        # ============================================
        # 6. CREATE FEATURE SETS
        # ============================================
        print("\n📐 6. Creating Feature Sets...")
        
        feature_sets = []
        active_model = [m for m in model_objects if m.is_active][0]
        
        for img in forensic_images[:25]:
            if img.image_type == "fingerprint":
                features = {
                    "minutiae": generate_sample_minutiae(),
                    "ridge_flow": {"pattern": "loop", "orientation": random.uniform(0, 180)},
                    "core_points": [{"x": 150, "y": 150, "type": "core"}]
                }
                minutiae_count = len(features["minutiae"])
            else:
                features = {
                    "striations": generate_sample_striations(),
                    "edge_profile": {"type": "parallel", "spacing": random.uniform(0.1, 0.5)},
                    "surface_roughness": random.uniform(0.1, 0.8)
                }
                minutiae_count = len(features["striations"])
            
            feature_set = FeatureSet(
                id=uuid.uuid4(),
                image_id=img.id,
                user_id=img.user_id,
                feature_vector=generate_sample_feature_vector(),
                extraction_time=random.uniform(0.2, 2.5),
                model_version_id=active_model.id,
                minutiae_points=features.get("minutiae", []),
                minutiae_count=minutiae_count,
                ridge_flow_pattern=features.get("ridge_flow", {}),
                striations=features.get("striations", []),
                confidence_scores={
                    "overall": random.uniform(0.85, 0.99),
                    "minutiae": random.uniform(0.8, 0.98)
                },
                feature_quality_score=random.uniform(0.75, 0.95),
                 
                created_at=datetime.now()
            )
            db.add(feature_set)
            feature_sets.append(feature_set)
            print(f"   ✓ Features extracted for: {img.original_filename} ({img.image_type}, {feature_set.minutiae_count} features)")
        
        db.flush()
        
        # ============================================
        # 7. CREATE SIMILARITY RESULTS
        # ============================================
        print("\n 7. Creating Similarity Results...")
        
        similarity_results = []
        for i in range(30):
            img1 = random.choice(forensic_images)
            img2 = random.choice([img for img in forensic_images if img.id != img1.id])
            
            # Generate realistic similarity score
            if img1.image_type == img2.image_type:
                similarity = random.uniform(0.6, 0.95) if random.random() > 0.5 else random.uniform(0.1, 0.4)
            else:
                similarity = random.uniform(0.05, 0.25)
            
            if similarity >= 0.75:
                match_status = "match"
                confidence = "high"
            elif similarity >= 0.6:
                match_status = "match"
                confidence = "medium"
            elif similarity >= 0.4:
                match_status = "inconclusive"
                confidence = "low"
            else:
                match_status = "non_match"
                confidence = "low"
            
            result = SimilarityResult(
                id=uuid.uuid4(),
                image1_id=img1.id,
                image2_id=img2.id,
                similarity_score=similarity * 100,
                match_status=match_status,
                confidence=confidence,
                matched_features=[
                    {"feature": f"point_{i}", "similarity": random.uniform(0.7, 0.98)}
                    for i in range(random.randint(5, 15))
                ],
                matched_feature_count=random.randint(5, 20),
                model_version=active_model.version,
                user_id=random.choice(analyst_users).id,
                analyst_verified=random.random() > 0.7,
                analyst_comment="Matches observed in ridge flow pattern" if random.random() > 0.8 else None,
                case_id=f"CASE-{random.randint(100, 999)}",
                created_at=datetime.now() - timedelta(days=random.randint(0, 15)),
                processing_time=random.uniform(0.3, 0.8)
            )
            db.add(result)
            similarity_results.append(result)
            print(f"   ✓ Comparison {i+1}: {img1.original_filename[:20]} vs {img2.original_filename[:20]} → {similarity*100:.1f}% ({match_status})")
        
        db.flush()
        
        # ============================================
        # 8. CREATE CASES
        # ============================================
        print("\n 8. Creating Cases...")
        
        cases = []
        case_statuses = ["open", "closed", "archived"]
        case_priorities = ["high", "medium", "low", "normal"]
        
        case_titles = [
            "Bank Robbery Investigation",
            "Residential Burglary",
            "Vehicle Theft",
            "Homicide Case #2024-001",
            "Counterfeit Operation",
            "Drug Trafficking",
            "Cyber Crime Investigation",
            "Missing Person Case",
            "Assault Investigation",
            "Property Crime Series"
        ]
        
        for i in range(10):
            case = Case(
                case_id=uuid.uuid4(),
                case_number=f"FED-2024-{1000 + i}",
                title=case_titles[i % len(case_titles)],
                description=f"Investigation into {case_titles[i % len(case_titles)].lower()}",
                status=random.choice(case_statuses),
                priority=random.choice(case_priorities),
                assigned_to=random.choice(analyst_users).id,
                created_by=admin.id,
                metadata={
                    "incident_date": (datetime.now() - timedelta(days=random.randint(1, 180))).isoformat(),
                    "location": f"Addis Ababa, Ethiopia",
                    "officer_in_charge": f"Detective {random.choice(['Tesfaye', 'Alemu', 'Girma', 'Mekonnen'])}",
                    "evidence_count": 0
                },
                created_at=datetime.now() - timedelta(days=random.randint(1, 180)),
                updated_at=datetime.now(),
                closed_at=datetime.now() - timedelta(days=random.randint(1, 30)) if random.random() > 0.7 else None
            )
            db.add(case)
            cases.append(case)
            print(f"   ✓ Created Case: {case.case_number} - {case.title} ({case.status})")
        
        db.flush()
        
        # ============================================
        # 9. LINK EVIDENCE TO CASES
        # ============================================
        print("\n🔗 9. Linking Evidence to Cases...")
        
        for case in cases:
            assigned_images = random.sample(forensic_images, min(random.randint(2, 5), len(forensic_images)))
            for img in assigned_images:
                link = CaseEvidence(
                    case_id=case.case_id,
                    image_id=img.id,
                    linked_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                    linked_by=random.choice(analyst_users).id
                )
                db.add(link)
            
            case.metadata["evidence_count"] = len(assigned_images)
            print(f"   ✓ Case {case.case_number}: {len(assigned_images)} evidence items linked")
        
        db.flush()
        
        # ============================================
        # 10. CREATE REPORTS
        # ============================================
        print("\n 10. Creating Reports...")
        
        for i, result in enumerate(similarity_results[:15]):
            analyst = random.choice(analyst_users)
            report = Report(
                id=uuid.uuid4(),
                user_id=result.user_id,
                similarity_result_id=result.id,
                report_path=f"/reports/report_{result.id}.pdf",
                report_filename=f"Forensic_Report_{datetime.now().strftime('%Y%m%d')}_{i+1}.pdf",
                report_format="PDF",
                case_number=result.case_id,
                report_summary={
                    "case_summary": f"Comparison of evidence items",
                    "findings": f"Similarity score of {result.similarity_score:.1f}% with {result.confidence} confidence",
                    "recommendation": "Further analysis recommended" if result.confidence == "low" else "Match confirmed"
                },
                generated_at=result.created_at + timedelta(hours=random.randint(1, 48)),
                is_shared=random.random() > 0.8,
                share_token=str(uuid.uuid4()) if random.random() > 0.8 else None
            )
            db.add(report)
            print(f"   ✓ Created Report for Case {result.case_id} (Score: {result.similarity_score:.1f}%)")
        
        db.flush()
        
        # ============================================
        # 11. CREATE AUDIT LOGS
        # ============================================
        print("\n 11. Creating Audit Logs...")
        
        actions = [
            "login", "login_failed", "logout", "image_uploaded", "image_processed",
            "similarity_compared", "report_generated", "user_created", "model_trained",
            "case_updated", "evidence_linked", "settings_changed"
        ]
        
        all_users = [admin, ai_engineer] + analyst_users
        
        for i in range(100):
            user = random.choice(all_users)
            action = random.choice(actions)
            timestamp = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            
            audit_log = AuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                user_email=user.email,
                user_role=user.role,
                action=action,
                timestamp=timestamp,
                ip_address=f"192.168.1.{random.randint(1, 255)}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                details={
                    "status": "success",
                    "resource": f"/api/v1/{action}",
                    "method": "POST" if action in ["login", "image_uploaded"] else "GET"
                },
                status="success" if random.random() > 0.1 else "failed"
            )
            db.add(audit_log)
        
        print(f"   ✓ Created {100} audit logs")
        
        # ============================================
        # 12. ADDITIONAL FEATURE SETS
        # ============================================
        print("\n 12. Adding Remaining Feature Sets...")
        
        for img in forensic_images[25:]:
            feature_set = FeatureSet(
                id=uuid.uuid4(),
                image_id=img.id,
                feature_vector=generate_sample_feature_vector(),
                extraction_time=random.uniform(0.2, 2.5),
                model_version_id=active_model.id,
                minutiae_points=generate_sample_minutiae() if img.image_type == "fingerprint" else [],
                minutiae_count=random.randint(10, 25) if img.image_type == "fingerprint" else 0,
                striations=generate_sample_striations() if img.image_type == "toolmark" else [],
                confidence_scores={"overall": random.uniform(0.85, 0.99)},
                feature_quality_score=random.uniform(0.75, 0.95),
                user_id=img.user_id,
                created_at=datetime.now()
            )
            db.add(feature_set)
            feature_sets.append(feature_set)
        
        print(f"   ✓ Total feature sets: {len(feature_sets)}")
        
        # ============================================
        # COMMIT ALL CHANGES
        # ============================================
        print("\n Committing all data to database...")
        db.commit()
        
        # ============================================
        # SUMMARY REPORT
        # ============================================
        print("\n" + "=" * 70)
        print("DATABASE SEEDING SUMMARY")
        print("=" * 70)
        print(f"   Users:              {db.query(User).count()}")
        print(f"   Forensic Images:    {db.query(ForensicImage).count()}")
        print(f"   Preprocessed:       {db.query(PreprocessedImage).count()}")
        print(f"   Feature Sets:       {db.query(FeatureSet).count()}")
        print(f"   Similarity Results: {db.query(SimilarityResult).count()}")
        print(f"   Reports:            {db.query(Report).count()}")
        print(f"   Audit Logs:         {db.query(AuditLog).count()}")
        print(f"   Datasets:           {db.query(Dataset).count()}")
        print(f"   Model Versions:     {db.query(ModelVersion).count()}")
        print(f"   Cases:              {db.query(Case).count()}")
        print(f"   Case Evidence:      {db.query(CaseEvidence).count()}")
        print("=" * 70)
        print("\n DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        
        # Print test credentials
        print("\n TEST CREDENTIALS:")
        print("   Admin:       abdi@forensicedge.com / Admin@123")
        print("   AI Engineer: abdullah@forensicedge.com / AIEngineer@123")
        print("   Analyst:     meron@forensicedge.com / Analyst@123")
        print("                meti@forensicedge.com / Analyst@123")
        print("                abebe@forensicedge.com / Analyst@123")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

# ============================================
# RUN THE SEEDER
# ============================================

if __name__ == "__main__":
    print("\n  WARNING: This will populate your database with sample data.")
    print("   If your database already has data, it will be preserved (no deletion).")
    response = input("   Continue? (y/N): ")
    
    if response.lower() == 'y':
        seed_database()
    else:
        print("❌ Seeding cancelled.")