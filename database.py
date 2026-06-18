import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./campaign_finance.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String) # presidential, gubernatorial, senatorial
    party = Column(String) # APC, PDP, LP, etc.
    state = Column(String, nullable=True) # For gubernatorial/senatorial
    estimated_spend = Column(Float, default=0.0)
    rallies_count = Column(Integer, default=0)

    rallies = relationship("Rally", back_populates="candidate", cascade="all, delete-orphan")

class Rally(Base):
    __tablename__ = "rallies"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    location = Column(String) # State or City
    buses = Column(Integer, default=0)
    bus_hire_cost = Column(Float, default=0.0)
    suvs = Column(Integer, default=0)
    fuel_liters = Column(Float, default=0.0)
    fuel_price = Column(Float, default=0.0)
    delegates = Column(Integer, default=0)
    allowance = Column(Float, default=0.0)
    venue_cost = Column(Float, default=0.0)
    publicity_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    source_url = Column(String, nullable=True) # If scraped

    candidate = relationship("Candidate", back_populates="rallies")

class StateSummary(Base):
    __tablename__ = "state_summaries"

    id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String, unique=True, index=True)
    total_rallies = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)
    limit_cap = Column(Float, default=1000000000.0) # 1 Billion default guber limit

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seed database with initial mockup datasets if empty
def seed_initial_data():
    db = SessionLocal()
    try:
        # Check if we already have candidates seeded
        if db.query(Candidate).count() == 0:
            print("Seeding initial campaign database...")
            
            # Seed Candidates
            cands = [
                Candidate(name="Asiwaju Bola Tinubu", category="presidential", party="APC", estimated_spend=135000000000.0, rallies_count=42),
                Candidate(name="Atiku Abubakar", category="presidential", party="PDP", estimated_spend=112000000000.0, rallies_count=38),
                Candidate(name="Peter Obi", category="presidential", party="LP", estimated_spend=24000000000.0, rallies_count=29),
                Candidate(name="Babajide Sanwo-Olu", category="gubernatorial", party="APC", state="Lagos", estimated_spend=18500000000.0, rallies_count=15),
                Candidate(name="Abdulrahman Abdulrazaq", category="gubernatorial", party="APC", state="Kwara", estimated_spend=4200000000.0, rallies_count=8),
                Candidate(name="Seyi Makinde", category="gubernatorial", party="PDP", state="Oyo", estimated_spend=6800000000.0, rallies_count=12),
                Candidate(name="Adams Oshiomhole", category="senatorial", party="APC", state="Edo", estimated_spend=1200000000.0, rallies_count=18),
            ]
            db.add_all(cands)
            db.commit()

            # Seed State Summaries
            states = [
                StateSummary(state_name="Lagos", total_rallies=45, total_spend=32000000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Kano", total_rallies=38, total_spend=24000000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Rivers", total_rallies=32, total_spend=28500000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Kaduna", total_rallies=24, total_spend=14500000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Oyo", total_rallies=18, total_spend=9500000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Enugu", total_rallies=14, total_spend=6200000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="Anambra", total_rallies=11, total_spend=5800000000.0, limit_cap=1000000000.0),
                StateSummary(state_name="FCT", total_rallies=28, total_spend=18000000000.0, limit_cap=1000000000.0),
            ]
            db.add_all(states)
            db.commit()
            print("Database seeding completed.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()
