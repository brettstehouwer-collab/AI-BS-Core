"""
FE Express — Fuel Cost, EIA Diesel Price Index & True Net Margin Calculator
Calculates real-world profitability for 26' Box Trucks and Hotshots:
  - National / Regional EIA Diesel Fuel Price Index
  - Average Fuel Efficiency (Class 6 Box Truck: ~9.5 MPG, Hotshot: ~12.5 MPG)
  - True Deadhead Radius & Dynamic Home Base
  - Maintenance & Toll Reserve per mile
  - Net Profit & Net Hourly Margin
"""

import math
from typing import Dict, Any

# Current US National On-Highway Diesel Fuel Index average ($/gal)
DEFAULT_DIESEL_PRICE_PER_GALLON = 3.85
DEFAULT_BOX_TRUCK_MPG = 9.5
DEFAULT_MAINTENANCE_PER_MILE = 0.25 # Tires, oil, DEF, wear & tear

class FuelCostCalculator:
    @staticmethod
    def calculate_trip_profitability(
        loaded_miles: float,
        deadhead_miles: float,
        flat_rate_pay: float,
        diesel_price_gal: float = DEFAULT_DIESEL_PRICE_PER_GALLON,
        truck_mpg: float = DEFAULT_BOX_TRUCK_MPG,
        driver_hourly_wage: float = 25.0,
        maint_cost_per_mile: float = DEFAULT_MAINTENANCE_PER_MILE,
        avg_highway_mph: float = 55.0
    ) -> Dict[str, Any]:
        """Calculates true cost of operation and net take-home for a freight run."""
        total_trip_miles = max(loaded_miles + deadhead_miles, 1.0)
        
        # Fuel calculations
        gallons_needed = round(total_trip_miles / max(truck_mpg, 1.0), 2)
        total_fuel_cost = round(gallons_needed * diesel_price_gal, 2)
        
        # Maintenance reserve
        maintenance_reserve = round(total_trip_miles * maint_cost_per_mile, 2)
        
        # Drive time
        est_driving_hours = round(total_trip_miles / max(avg_highway_mph, 1.0), 2)
        est_driver_cost = round(est_driving_hours * driver_hourly_wage, 2)
        
        # Total Operating Cost (Fuel + Maint + Labor)
        total_operating_expense = round(total_fuel_cost + maintenance_reserve + est_driver_cost, 2)
        net_profit = round(flat_rate_pay - total_operating_expense, 2)
        
        net_rpm = round(net_profit / total_trip_miles, 2)
        net_hourly_rate = round(net_profit / max(est_driving_hours, 0.1), 2)
        
        # Profit Margin percentage
        profit_margin_pct = round((net_profit / max(flat_rate_pay, 1.0)) * 100, 1)

        return {
            "total_trip_miles": total_trip_miles,
            "loaded_miles": loaded_miles,
            "deadhead_miles": deadhead_miles,
            "gross_revenue": flat_rate_pay,
            "gross_rpm": round(flat_rate_pay / max(loaded_miles, 1.0), 2),
            "diesel_price_gal": diesel_price_gal,
            "fuel_expense": total_fuel_cost,
            "gallons_consumed": gallons_needed,
            "maintenance_reserve": maintenance_reserve,
            "estimated_driving_hours": est_driving_hours,
            "driver_labor_cost": est_driver_cost,
            "total_operating_expense": total_operating_expense,
            "net_profit": net_profit,
            "net_rpm": net_rpm,
            "net_hourly_rate": net_hourly_rate,
            "profit_margin_pct": profit_margin_pct,
            "is_profitable": net_profit > 0 and net_rpm >= 0.50
        }
