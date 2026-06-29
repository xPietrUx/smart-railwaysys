from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/hello")
def get_welcome_message():
	return {"message": "Połączenie z backendem udane"}
