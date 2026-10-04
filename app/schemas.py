from pydantic import BaseModel, ConfigDict, Field, StrictBool


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Location(InputModel):
    province: str = Field(min_length=1)
    city: str = Field(min_length=1)


class Component(InputModel):
    wind_load_pa: float | None = Field(default=None, gt=0)
    snow_load_pa: float | None = Field(default=None, gt=0)
    hail_diameter_mm: float | None = Field(default=None, gt=0)


class Mounting(InputModel):
    secure: StrictBool | None = None


class Building(InputModel):
    roof_sound: StrictBool | None = None


class Protection(InputModel):
    drainage_good: StrictBool | None = None
    equipment_height_m: float | None = Field(default=None, ge=0)
    lightning_protection: StrictBool | None = None
    grounding_verified: StrictBool | None = None


class RiskInput(InputModel):
    project_id: str | None = None
    location: Location | None = None
    project_type: str = Field(min_length=1)
    installed_capacity_kw: float = Field(gt=0)
    component: Component = Field(default_factory=Component)
    mounting_system: Mounting = Field(default_factory=Mounting)
    building: Building = Field(default_factory=Building)
    protection: Protection = Field(default_factory=Protection)
    evidence_references: list[str] = Field(default_factory=list)


class DisasterResult(BaseModel):
    disaster: str
    name: str
    exposure_score: float | None
    resilience_score: float | None
    risk_score: float | None
    risk_level: str
    evidence: list[str]
    missing_fields: list[str]


class RiskOutput(BaseModel):
    project_id: str | None
    rule_version: str
    assessment_status: str
    disaster_resilience_score: float | None
    claim_risk_score: float | None
    risk_level: str
    decision_support: str
    highlighted_risks: list[str]
    risk_breakdown: list[DisasterResult]
    required_follow_up_materials: list[str]
    evidence_references: list[str]
    data_source: dict
    limitations: list[str]
