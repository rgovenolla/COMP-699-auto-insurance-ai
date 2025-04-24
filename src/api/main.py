from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import jwt
import time
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classifiers.enhanced_scenario_classifier import EnhancedScenarioClassifier
from src.policy_analyzer import PolicyAnalyzer
from src.risk_assessor import RiskAssessor
from src.explanation_generator import ExplanationGenerator
from src.recommendation_engine import RecommendationEngine
from src.utils.performance_monitor import PerformanceMonitor
from src.config.settings import settings

# Initialize performance monitoring
performance_monitor = PerformanceMonitor()

# Models
class ScenarioRequest(BaseModel):
    scenario_text: str = Field(..., min_length=10, max_length=5000)
    include_explanation: bool = True
    include_recommendations: bool = True
    user_policy: Optional[Dict] = None
    user_profile: Optional[Dict] = None

class ClassificationResponse(BaseModel):
    category: str
    confidence: float
    relevant_policies: List[str]
    risk_assessment: Optional[Dict] = None
    policy_analysis: Optional[Dict] = None
    explanation: Optional[Dict] = None
    recommendations: Optional[List[Dict]] = None
    processing_time: Optional[float] = None

class TokenData(BaseModel):
    username: str
    scopes: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float

# API setup
app = FastAPI(
    title="Auto Insurance Liability AI API",
    description="API for auto insurance scenario classification and analysis",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Security setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Mock database - would be replaced with actual DB in production
fake_users_db = {
    "demo": {
        "username": "demo",
        "email": "demo@example.com",
        "disabled": False,
        "password": "password"  # Would be properly hashed in production
    },
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "disabled": False,
        "password": "admin"  # Would be properly hashed in production
    }
}

# Start time for uptime tracking
start_time = time.time()

# Helper functions
def get_user(username: str):
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(
            username=user_dict["username"],
            email=user_dict.get("email"),
            disabled=user_dict.get("disabled", False)
        )
    return None

def authenticate_user(username: str, password: str):
    if username not in fake_users_db:
        return False
    user_dict = fake_users_db[username]
    if user_dict["password"] != password:  # Would use proper password verification in production
        return False
    return get_user(username)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, scopes=payload.get("scopes", []))
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user

# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    start_time = time.time()

    # Process the request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Track metrics only for API endpoints
    if request.url.path.startswith("/api/v1/"):
        await performance_monitor.track_request(
            request_type=request.url.path,
            start_time=start_time,
            end_time=time.time(),
            success=response.status_code < 400,
            details={"status_code": response.status_code}
        )

    return response

# API routes
@app.post("/api/v1/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Determine scopes based on user
    scopes = ["classify"]
    if user.username == "admin":
        scopes.extend(["analyze", "metrics"])

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expire_time = create_access_token(
        data={"sub": user.username, "scopes": scopes},
        expires_delta=access_token_expires
    )

    # Calculate expiration in seconds
    expires_in = int((expire_time - datetime.utcnow()).total_seconds())

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in
    }

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "uptime": time.time() - start_time
    }

@app.post("/api/v1/classify", response_model=ClassificationResponse)
async def classify_scenario(
    request: ScenarioRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Classify and analyze an insurance scenario.

    This endpoint provides comprehensive analysis of auto insurance scenarios, including
    classification, policy analysis, risk assessment, explanations, and recommendations.
    """
    request_start_time = time.time()

    try:
        # Initialize classifier
        classifier = EnhancedScenarioClassifier()

        # Classify scenario
        classification = await classifier.classify_scenario(request.scenario_text)

        response = ClassificationResponse(
            category=classification["category"],
            confidence=classification["confidence"],
            relevant_policies=classification["relevant_policies"]
        )

        # Initialize additional components
        policy_analyzer = PolicyAnalyzer()
        risk_assessor = RiskAssessor()

        # Perform analysis
        policy_analysis = policy_analyzer.analyze_policies(
            classification,
            user_policy=request.user_policy
        )

        risk_assessment = await risk_assessor.assess_risk(
            classification,
            request.scenario_text
        )

        # Add to response
        response.policy_analysis = policy_analysis
        response.risk_assessment = risk_assessment

        # Add explanation if requested
        if request.include_explanation:
            explanation_generator = ExplanationGenerator()
            explanation = await explanation_generator.generate_explanation(
                classification, policy_analysis, risk_assessment
            )
            response.explanation = explanation

        # Add recommendations if requested
        if request.include_recommendations:
            recommendation_engine = RecommendationEngine()
            recommendations = await recommendation_engine.generate_recommendations(
                classification,
                policy_analysis,
                risk_assessment,
                user_profile=request.user_profile
            )
            response.recommendations = recommendations

        # Calculate and add processing time
        processing_time = time.time() - request_start_time
        response.processing_time = round(processing_time, 4)

        # Track successful classification
        await performance_monitor.track_request(
            request_type="classification",
            start_time=request_start_time,
            end_time=time.time(),
            success=True,
            details={
                "category": classification["category"],
                "confidence": classification["confidence"],
                "rule_based_fallback": classification.get("rule_based_fallback", False)
            }
        )

        return response
    except Exception as e:
        # Track failed classification
        await performance_monitor.track_request(
            request_type="classification",
            start_time=request_start_time,
            end_time=time.time(),
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")

@app.get("/api/v1/metrics")
async def get_metrics(current_user: User = Depends(get_current_user)):
    """Get API performance metrics."""
    # Check if user has metrics scope
    try:
        payload = jwt.decode(
            await oauth2_scheme(Request(scope={"type": "http"})),
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        if "metrics" not in payload.get("scopes", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access metrics"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access metrics"
        )

    report = await performance_monitor.get_performance_report()
    return report
