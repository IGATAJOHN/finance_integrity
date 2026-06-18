from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uvicorn
import os

from database import get_db, seed_initial_data, Candidate, Rally, StateSummary
from scraper import scrape_article
from discoverer import discover_rallies

app = FastAPI(title="PoliTrack API", description="Nigeria Campaign Finance Integrity Backend")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize and seed database
@app.on_event("startup")
def startup_event():
    seed_initial_data()

# Schemas
class RallyCreate(BaseModel):
    candidate_id: int
    location: str
    buses: int
    bus_hire_cost: float
    suvs: int
    fuel_liters: float
    fuel_price: float
    delegates: int
    allowance: float
    venue_cost: float
    publicity_cost: float
    source_url: Optional[str] = None

class ScrapeRequest(BaseModel):
    url: str

class DiscoverRequest(BaseModel):
    candidate_name: str

# Endpoints
@app.get("/api/candidates")
def get_candidates(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    # Format candidates list
    return [
        {
            "id": cand.id,
            "name": cand.name,
            "category": cand.category,
            "party": cand.party,
            "state": cand.state,
            "estimatedSpend": cand.estimated_spend,
            "ralliesHeld": cand.rallies_count,
            "breakdown": {
                "buses": sum(r.buses * r.bus_hire_cost for r in cand.rallies) or (cand.estimated_spend * 0.25),
                "delegates": sum(r.delegates * r.allowance for r in cand.rallies) or (cand.estimated_spend * 0.35),
                "media": sum(r.publicity_cost for r in cand.rallies) or (cand.estimated_spend * 0.25),
                "logistics": sum(r.venue_cost + ((r.buses + r.suvs) * r.fuel_liters * r.fuel_price) for r in cand.rallies) or (cand.estimated_spend * 0.15),
            }
        }
        for cand in candidates
    ]

@app.get("/api/states")
def get_states(db: Session = Depends(get_db)):
    states = db.query(StateSummary).all()
    result = {}
    for s in states:
        # Get candidates associated with this state
        cands = db.query(Candidate).filter(Candidate.state == s.state_name).all()
        cand_list = [f"{c.name} ({c.party})" for c in cands]
        
        # Heatmap coloring
        color = "#10b981" # Green
        ratio = s.total_spend / s.limit_cap
        if ratio > 15:
            color = "#ef4444" # Red
        elif ratio > 2:
            color = "#f59e0b" # Orange
        elif ratio > 0.5:
            color = "#3b82f6" # Blue

        result[s.state_name] = {
            "rallies": s.total_rallies,
            "spend": s.total_spend,
            "limit": s.limit_cap,
            "color": color,
            "candidates": cand_list or ["No local candidates registered"]
        }
    return result

@app.post("/api/rallies")
def create_rally(rally_data: RallyCreate, db: Session = Depends(get_db)):
    # Verify candidate exists
    cand = db.query(Candidate).filter(Candidate.id == rally_data.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Calculate costs
    bus_total = rally_data.buses * rally_data.bus_hire_cost
    fuel_total = (rally_data.buses + rally_data.suvs) * rally_data.fuel_liters * rally_data.fuel_price
    delegate_total = rally_data.delegates * rally_data.allowance
    venue_pub_total = rally_data.venue_cost + rally_data.publicity_cost
    total_cost = bus_total + fuel_total + delegate_total + venue_pub_total

    # Add Rally record
    db_rally = Rally(
        candidate_id=rally_data.candidate_id,
        location=rally_data.location,
        buses=rally_data.buses,
        bus_hire_cost=rally_data.bus_hire_cost,
        suvs=rally_data.suvs,
        fuel_liters=rally_data.fuel_liters,
        fuel_price=rally_data.fuel_price,
        delegates=rally_data.delegates,
        allowance=rally_data.allowance,
        venue_cost=rally_data.venue_cost,
        publicity_cost=rally_data.publicity_cost,
        total_cost=total_cost,
        source_url=rally_data.source_url
    )
    db.add(db_rally)

    # Update candidate total spend and rally count
    cand.estimated_spend += total_cost
    cand.rallies_count += 1

    # Update or Create State Summary details
    state_sum = db.query(StateSummary).filter(StateSummary.state_name == rally_data.location).first()
    if not state_sum:
        state_sum = StateSummary(state_name=rally_data.location, total_rallies=1, total_spend=total_cost)
        db.add(state_sum)
    else:
        state_sum.total_rallies += 1
        state_sum.total_spend += total_cost

    db.commit()
    db.refresh(cand)

    return {"message": "Rally log added successfully", "total_rally_cost": total_cost, "candidate_new_total": cand.estimated_spend}

@app.post("/api/scrape")
def scrape_and_estimate(request: ScrapeRequest):
    result = scrape_article(request.url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/discover")
def discover_campaign_rallies(request: DiscoverRequest):
    result = discover_rallies(request.candidate_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/reset")
def reset_database(db: Session = Depends(get_db)):
    # Clear tables
    db.query(Rally).delete()
    db.query(Candidate).delete()
    db.query(StateSummary).delete()
    db.commit()
    # Reseed
    seed_initial_data()
    return {"message": "Database reset to initial mock values completed."}

# Serve static frontend files (Single Page Application)
# Make sure to run this line last so it doesn't override API routes
if os.path.exists("./index.html"):
    app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
