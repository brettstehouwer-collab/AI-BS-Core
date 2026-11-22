# Attach calendar integration to the AI-BS FastAPI app
# Add this AFTER the FastAPI app is initialized (after app = FastAPI(...))

from calendar_integration import get_calendar_routes
from memory_service import get_memory_service

# Inject calendar routes
get_calendar_routes(app, get_memory_service)

print("[Calendar] Integrated with AI-BS Matrix. Available endpoints:")
print("  GET  /api/calendar/appointments")
print("  POST /api/calendar/appointments")
print("  POST /api/calendar/nlp/parse")
print("  PUT  /api/calendar/appointments/{id}")
print("  DEL  /api/calendar/appointments/{id}")
print("  GET  /api/calendar/search?query=...")
