"""
Mahmoud Dessoki Portfolio - FastAPI Backend
Full-stack portfolio management system with admin dashboard
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import shutil
import uuid
import jwt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Create FastAPI app
app = FastAPI(
    title="Mahmoud Dessoki Portfolio API",
    description="Portfolio management system with admin dashboard",
    version="1.0.0"
)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# CORS configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://lensmania.ae",
    "https://www.lensmania.ae",
]
extra = os.getenv("EXTRA_ORIGINS", "")
if extra:
    ALLOWED_ORIGINS += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== DATABASE MODELS ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Work, Events, Social Media, Food, Podcasts, YouTube
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    video_type = Column(String, default="youtube")  # youtube, vimeo, direct
    embed_code = Column(Text, nullable=True)
    views = Column(Integer, default=0)
    featured = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class About(Base):
    __tablename__ = "about"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    bio = Column(Text)
    image_url = Column(String, nullable=True)
    skills = Column(Text)  # JSON string of skills
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    site_title = Column(String, default="Mahmoud Dessoki")
    site_description = Column(Text)
    email = Column(String)
    phone = Column(String, nullable=True)
    location = Column(String, default="Dubai, UAE")
    instagram = Column(String, nullable=True)
    youtube = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Seed admin user from .env on first run
def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin_email = os.getenv("ADMIN_EMAIL", "admin@lensmania.ae")
            admin_password = os.getenv("ADMIN_PASSWORD", "change-this-password")
            db.add(User(email=admin_email, password_hash=admin_password))
            db.commit()
    finally:
        db.close()

_seed_admin()

# ==================== PYDANTIC SCHEMAS ====================

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    order: int
    
    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    category_id: int
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    video_type: str = "youtube"
    embed_code: Optional[str] = None
    featured: bool = False
    order: int = 0

class PortfolioUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    video_type: Optional[str] = None
    embed_code: Optional[str] = None
    featured: Optional[bool] = None
    order: Optional[int] = None

class PortfolioResponse(BaseModel):
    id: int
    category_id: int
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    video_url: Optional[str]
    video_type: str
    embed_code: Optional[str]
    views: int
    featured: bool
    order: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AboutCreate(BaseModel):
    title: str
    bio: str
    image_url: Optional[str] = None
    skills: str  # JSON string

class AboutResponse(BaseModel):
    id: int
    title: str
    bio: str
    image_url: Optional[str]
    skills: str
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SettingsResponse(BaseModel):
    id: int
    site_title: str
    site_description: str
    email: str
    phone: Optional[str]
    location: str
    instagram: Optional[str]
    youtube: Optional[str]
    linkedin: Optional[str]
    
    class Config:
        from_attributes = True

# ==================== DEPENDENCY INJECTION ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return email

# ==================== AUTHENTICATION ROUTES ====================

@app.post("/api/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Admin login endpoint"""
    # In production, hash passwords with bcrypt
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or user.password_hash != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {"sub": user.email, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# ==================== CATEGORY ROUTES ====================

@app.get("/api/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Get all portfolio categories"""
    categories = db.query(Category).order_by(Category.order).all()
    return categories

@app.post("/api/categories", response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create new portfolio category (admin only)"""
    db_category = Category(
        name=category.name,
        slug=category.slug,
        description=category.description
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# ==================== PORTFOLIO ROUTES ====================

@app.get("/api/portfolio", response_model=List[PortfolioResponse])
def get_portfolio(
    category: Optional[str] = None,
    featured: bool = False,
    db: Session = Depends(get_db)
):
    """Get portfolio items, optionally filtered by category"""
    query = db.query(Portfolio)
    
    if category:
        cat = db.query(Category).filter(Category.slug == category).first()
        if cat:
            query = query.filter(Portfolio.category_id == cat.id)
    
    if featured:
        query = query.filter(Portfolio.featured == True)
    
    items = query.order_by(Portfolio.order).all()
    return items

@app.get("/api/portfolio/{item_id}", response_model=PortfolioResponse)
def get_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    """Get specific portfolio item"""
    item = db.query(Portfolio).filter(Portfolio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    
    # Increment view count
    item.views += 1
    db.commit()
    return item

@app.post("/api/portfolio", response_model=PortfolioResponse)
def create_portfolio_item(
    portfolio: PortfolioCreate,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create new portfolio item (admin only)"""
    db_portfolio = Portfolio(**portfolio.model_dump())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@app.put("/api/portfolio/{item_id}", response_model=PortfolioResponse)
def update_portfolio_item(
    item_id: int,
    portfolio: PortfolioUpdate,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update portfolio item (admin only)"""
    db_item = db.query(Portfolio).filter(Portfolio.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    
    update_data = portfolio.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db_item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/portfolio/{item_id}")
def delete_portfolio_item(
    item_id: int,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Delete portfolio item (admin only)"""
    db_item = db.query(Portfolio).filter(Portfolio.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    
    db.delete(db_item)
    db.commit()
    return {"message": "Portfolio item deleted"}

# ==================== ABOUT ROUTES ====================

@app.get("/api/about", response_model=AboutResponse)
def get_about(db: Session = Depends(get_db)):
    """Get about section content"""
    about = db.query(About).first()
    if not about:
        raise HTTPException(status_code=404, detail="About section not found")
    return about

@app.put("/api/about", response_model=AboutResponse)
def update_about(
    about_data: AboutCreate,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update about section (admin only)"""
    about = db.query(About).first()
    if not about:
        about = About(**about_data.model_dump())
        db.add(about)
    else:
        for field, value in about_data.model_dump().items():
            setattr(about, field, value)
    
    db.commit()
    db.refresh(about)
    return about

# ==================== SETTINGS ROUTES ====================

@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get site settings"""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(
            site_title="Mahmoud Dessoki",
            site_description="Professional Cinematographer & Videographer",
            email="info@lensmania.ae"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@app.put("/api/settings", response_model=SettingsResponse)
def update_settings(
    settings_data: SettingsResponse,
    email: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update site settings (admin only)"""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(**settings_data.model_dump())
        db.add(settings)
    else:
        for field, value in settings_data.model_dump(exclude={"id"}).items():
            setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    return settings

# ==================== FILE UPLOAD ====================

ALLOWED_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.webm',
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
}

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    email: str = Depends(verify_token),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed")

    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    with dest.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return {"url": f"/uploads/{filename}", "filename": filename}

# ==================== HEALTH CHECK ====================

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow()}

# ==================== ROOT ====================

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Mahmoud Dessoki Portfolio API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
