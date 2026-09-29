"""Onboarding, dashboard, and notification endpoints under /api/v1/user."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas.user import OnboardingRequest, DashboardResponse
from ..core.security import get_current_user
router = APIRouter()

@router.put("/onboarding", response_model=DashboardResponse)
def onboarding(payload: OnboardingRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.risk_profile, user.investment_horizon, user.widgets = payload.risk_profile, payload.investment_horizon, payload.widgets
    db.commit()
    return DashboardResponse(email=user.email, risk_profile=user.risk_profile, investment_horizon=user.investment_horizon, widgets=user.widgets)

@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: User = Depends(get_current_user)):
    return DashboardResponse(email=user.email, risk_profile=user.risk_profile, investment_horizon=user.investment_horizon, widgets=user.widgets or [])
