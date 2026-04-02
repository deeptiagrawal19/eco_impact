"""External data clients and shared service utilities."""

from app.services.electricity_maps import ElectricityMapsClient
from app.services.impact_calculator import AImpactCalculator, get_model_by_identifier
from app.services.watttime import (
    ELECTRICITY_MAPS_TO_WATTTIME,
    WattTimeClient,
    map_em_zone_to_watttime,
)

__all__ = [
    "AImpactCalculator",
    "ELECTRICITY_MAPS_TO_WATTTIME",
    "ElectricityMapsClient",
    "WattTimeClient",
    "get_model_by_identifier",
    "map_em_zone_to_watttime",
]
