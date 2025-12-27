"""
Structured output schemas for consistent agent responses
"""
from pydantic import BaseModel
from typing import List, Optional

class CostBreakdown(BaseModel):
    component: str
    service: str
    monthly_cost: float
    details: str

class CostAnalysis(BaseModel):
    total_monthly_cost: float
    breakdown: List[CostBreakdown]
    summary: str
    recommendations: Optional[List[str]] = None

class PRAnalysis(BaseModel):
    security_score: int  # 1-10
    security_issues: List[str]
    best_practices_score: int  # 1-10
    best_practices_issues: List[str]
    summary: str
    recommendations: List[str]

class DeploymentStatus(BaseModel):
    status: str
    run_id: str
    success: bool
    message: str
    duration_seconds: Optional[int] = None
