"""
Quantitative Analytics, DuckDB & Project NOCO Spatial Router
Exposes endpoints for:
- POST /api/v1/analytics/duckdb/query
- POST /api/v1/crypto/indicators/calculate
- POST /api/v1/infrastructure/noco/spatial
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from core.quantitative_spatial_analytics_engine import QuantitativeSpatialAnalyticsEngine

router = APIRouter(prefix="/api/v1", tags=["Quantitative Analytics & Spatial"])


class DuckDbQueryRequest(BaseModel):
    sql_query: str = Field(..., description="SQL query to run across attached SQLite/Parquet databases")
    databases_to_attach: Optional[List[str]] = Field(default=None, description="Optional custom DB alias list")
    max_rows: int = Field(default=100, description="Max rows to return")


class TechnicalIndicatorsRequest(BaseModel):
    prices: List[float] = Field(..., description="Ordered list of historical asset prices")
    volumes: Optional[List[float]] = Field(default=None, description="Optional volume series")
    rsi_period: int = Field(default=14, description="RSI lookback period")
    bollinger_period: int = Field(default=20, description="Bollinger lookback period")


class NocoSpatialRequest(BaseModel):
    facility_sq_ft: float = Field(default=2400.0, description="Total building square footage")
    growing_tiers: int = Field(default=4, description="Number of vertical growing rack levels")
    crop_type: str = Field(default="leafy_greens_and_herbs", description="Target crop classification")
    stage_sq_ft: float = Field(default=600.0, description="Dedicated live performance stage square footage")
    ceiling_height_ft: float = Field(default=18.0, description="Facility ceiling height in feet")


@router.post("/analytics/duckdb/query")
async def duckdb_query_endpoint(req: DuckDbQueryRequest):
    try:
        res = QuantitativeSpatialAnalyticsEngine.execute_duckdb_query(
            sql_query=req.sql_query,
            databases_to_attach=req.databases_to_attach,
            max_rows=req.max_rows
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crypto/indicators/calculate")
async def indicators_endpoint(req: TechnicalIndicatorsRequest):
    try:
        res = QuantitativeSpatialAnalyticsEngine.calculate_technical_indicators(
            prices=req.prices,
            volumes=req.volumes,
            rsi_period=req.rsi_period,
            bollinger_period=req.bollinger_period
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infrastructure/noco/spatial")
async def noco_spatial_endpoint(req: NocoSpatialRequest):
    try:
        res = QuantitativeSpatialAnalyticsEngine.calculate_noco_spatial_parameters(
            facility_sq_ft=req.facility_sq_ft,
            growing_tiers=req.growing_tiers,
            crop_type=req.crop_type,
            stage_sq_ft=req.stage_sq_ft,
            ceiling_height_ft=req.ceiling_height_ft
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
