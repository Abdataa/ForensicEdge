"""
backend/app/schemas/case_schema.py
-------------------------------------
Pydantic schemas for the Case Management Subsystem.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.models.case import CaseStatus, CasePriority


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
from enum import Enum


class CaseMemberRole(str, Enum):
    LEAD_INVESTIGATOR      = "lead_investigator"
    ASSISTANT_INVESTIGATOR = "assistant_investigator"
    AI_SUPPORT             = "ai_support"
    REVIEWER               = "reviewer"
    OBSERVER               = "observer"

class CaseMemberAdd(BaseModel):
    user_id: int
    case_role: CaseMemberRole
    notes: Optional[str] = Field(None, max_length=255)

class CaseCreate(BaseModel):
    """Body for POST /api/v1/cases"""
    title: str = Field(
        ..., min_length=3, max_length=255,
        examples=["Case #2025-001 Robbery Scene"],
    )
    description: Optional[str] = Field(
        None, max_length=2000,
        examples=["Fingerprint evidence collected from scene B, locker 14."],
    )


    priority: CasePriority = Field(default=CasePriority.MEDIUM)
    status:   CaseStatus   = Field(default=CaseStatus.OPEN)
        # Optional initial members
    members: list[CaseMemberAdd] = []


class CaseUpdate(BaseModel):
    """Body for PUT /api/v1/cases/{id} — all fields optional"""
    title:       Optional[str]          = Field(None, min_length=3, max_length=255)
    description: Optional[str]          = Field(None, max_length=2000)

    priority:    Optional[CasePriority] = None
    status:      Optional[CaseStatus]   = None


class LinkEvidenceRequest(BaseModel):
    """Body for POST /api/v1/cases/{id}/evidence"""
    image_id: int = Field(..., description="ID of the ForensicImage to link")
    notes:    Optional[str] = Field(None, max_length=500)


class LinkAnalysisRequest(BaseModel):
    """Body for POST /api/v1/cases/{id}/analyses"""
    result_id: int = Field(..., description="ID of the SimilarityResult to link")


class LinkReportRequest(BaseModel):
    """Body for POST /api/v1/cases/{id}/reports"""
    report_id: int = Field(..., description="ID of the Report to link")


class CaseNoteCreate(BaseModel):
    """Body for POST /api/v1/cases/{id}/notes"""
    note_text: str = Field(..., min_length=1, max_length=5000)





class CaseMemberUpdate(BaseModel):
    case_role: Optional[CaseMemberRole] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=255)

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CaseNoteResponse(BaseModel):
    id:         int
    case_id:    int
    user_id:    Optional[int]
    note_text:  str
    created_at: datetime

    model_config = {"from_attributes": True}

class CaseEvidenceResponse(BaseModel):
    id:        int
    case_id:   int
    image_id:  int
    linked_by: Optional[int]
    linked_at: datetime
    notes:     Optional[str]

    model_config = {"from_attributes": True}


class CaseAnalysisResponse(BaseModel):
    id:        int
    case_id:   int
    result_id: int
    added_at:  datetime

    model_config = {"from_attributes": True}


class CaseReportResponse(BaseModel):
    id:        int
    case_id:   int
    report_id: int
    added_at:  datetime

    model_config = {"from_attributes": True}

class CaseMemberResponse(BaseModel):
    id: int

    case_id: int
    user_id: int

    case_role: CaseMemberRole

    assigned_by: Optional[int]

    assigned_at: datetime

    is_active: bool

    notes: Optional[str]

    model_config = {"from_attributes": True}

class CaseResponse(BaseModel):
    """Full case details returned to client."""
    id:          int
    title:       str
    description: Optional[str]
    created_by:  Optional[int]

    status:      CaseStatus
    priority:    CasePriority
    created_at:  datetime
    updated_at:  datetime

    # Counts (populated by service, not from ORM directly)
    evidence_count:  int = 0
    analyses_count:  int = 0
    reports_count:   int = 0
    notes_count:     int = 0
    members: list[CaseMemberResponse] = []
    model_config = {"from_attributes": True}



class CaseListResponse(BaseModel):
    total:  int
    page:   int
    limit:  int
    cases:  list[CaseResponse]


class CaseDetailResponse(CaseResponse):
    """Extended case details with linked items."""
    evidence:  list[CaseEvidenceResponse]  = []
    analyses:  list[CaseAnalysisResponse]  = []
    reports:   list[CaseReportResponse]    = []
    notes:     list[CaseNoteResponse]      = []\


