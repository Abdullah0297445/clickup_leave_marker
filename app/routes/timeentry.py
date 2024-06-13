from fastapi import APIRouter
from fastapi import status

router = APIRouter()


@router.post("/")
async def create_entry(status_code=status.HTTP_204_NO_CONTENT) -> None:
    """
    Create a time entry from 9AM - 5PM on the day of the leave.
    """
    print("Time tracked")
