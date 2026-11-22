"""Explicit source registration for owner-scoped capture; never activate on import."""
import os


def register_driver_portal(app):
    """Mount only with the exact opt-in, independently of shared FE PIN routes."""
    if os.environ.get('AI_BS_ENABLE_DRIVER_PORTAL') != '1':
        return False
    from fe_express_owned_records import router
    from fe_truck_profiles import router as truck_router

    app.include_router(router)
    app.include_router(truck_router)
    return True
