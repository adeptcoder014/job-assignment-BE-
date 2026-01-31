from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hrms.db")
SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    department = Column(String, nullable=False)

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # "Present" or "Absent"

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class EmployeeCreate(BaseModel):
    employee_id: str
    full_name: str
    email: EmailStr
    department: str
    
    @validator('employee_id')
    def validate_employee_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Employee ID cannot be empty')
        return v.strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()
    
    @validator('department')
    def validate_department(cls, v):
        if not v or not v.strip():
            raise ValueError('Department cannot be empty')
        return v.strip()

class EmployeeResponse(BaseModel):
    id: int
    employee_id: str
    full_name: str
    email: str
    department: str
    
    class Config:
        from_attributes = True

class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    status: str
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ['Present', 'Absent']:
            raise ValueError('Status must be either "Present" or "Absent"')
        return v

class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    status: str
    employee_name: Optional[str] = None
    employee_employee_id: Optional[str] = None
    
    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(title="HRMS Lite API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Routes

@app.get("/")
def root():
    return {"message": "HRMS Lite API"}

# Employee endpoints
@app.post("/api/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    # Check for duplicate employee_id
    existing = db.query(Employee).filter(Employee.employee_id == employee.employee_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")
    
    # Check for duplicate email
    existing_email = db.query(Employee).filter(Employee.email == employee.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    db_employee = Employee(
        employee_id=employee.employee_id,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@app.get("/api/employees", response_model=List[EmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return employees

@app.get("/api/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.delete("/api/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Delete associated attendance records
    db.query(Attendance).filter(Attendance.employee_id == employee_id).delete()
    db.delete(employee)
    db.commit()
    return None

# Attendance endpoints
@app.post("/api/attendance", response_model=AttendanceResponse, status_code=201)
def create_attendance(attendance: AttendanceCreate, db: Session = Depends(get_db)):
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.id == attendance.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check for duplicate attendance on same date
    existing = db.query(Attendance).filter(
        Attendance.employee_id == attendance.employee_id,
        Attendance.date == attendance.date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked for this date")
    
    db_attendance = Attendance(
        employee_id=attendance.employee_id,
        date=attendance.date,
        status=attendance.status
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    
    # Include employee info in response
    response = AttendanceResponse(
        id=db_attendance.id,
        employee_id=db_attendance.employee_id,
        date=db_attendance.date,
        status=db_attendance.status,
        employee_name=employee.full_name,
        employee_employee_id=employee.employee_id
    )
    return response

@app.get("/api/attendance", response_model=List[AttendanceResponse])
def get_attendance(employee_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Attendance)
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    
    attendance_records = query.order_by(Attendance.date.desc()).all()
    
    # Include employee info
    result = []
    for record in attendance_records:
        employee = db.query(Employee).filter(Employee.id == record.employee_id).first()
        result.append(AttendanceResponse(
            id=record.id,
            employee_id=record.employee_id,
            date=record.date,
            status=record.status,
            employee_name=employee.full_name if employee else None,
            employee_employee_id=employee.employee_id if employee else None
        ))
    return result

@app.get("/api/attendance/employee/{employee_id}", response_model=List[AttendanceResponse])
def get_employee_attendance(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    attendance_records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id
    ).order_by(Attendance.date.desc()).all()
    
    result = []
    for record in attendance_records:
        result.append(AttendanceResponse(
            id=record.id,
            employee_id=record.employee_id,
            date=record.date,
            status=record.status,
            employee_name=employee.full_name,
            employee_employee_id=employee.employee_id
        ))
    return result

# Bonus: Dashboard stats
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total_employees = db.query(Employee).count()
    total_attendance = db.query(Attendance).count()
    present_count = db.query(Attendance).filter(Attendance.status == "Present").count()
    
    # Get present days per employee
    employees = db.query(Employee).all()
    employee_stats = []
    for emp in employees:
        present_days = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.status == "Present"
        ).count()
        employee_stats.append({
            "employee_id": emp.employee_id,
            "employee_name": emp.full_name,
            "present_days": present_days
        })
    
    return {
        "total_employees": total_employees,
        "total_attendance_records": total_attendance,
        "total_present": present_count,
        "employee_stats": employee_stats
    }

