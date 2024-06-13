from fastapi import APIRouter
from fastapi import status
from pydantic import Field, SecretStr, BaseModel, EmailStr
import os

router = APIRouter()


class AssigneeSchema(BaseModel):
    id: int
    username: str
    email: EmailStr

class PayloadSchema(BaseModel):
    assignees: list[AssigneeSchema] = Field(default_factory=list)
    custom_fields: list[dict] = Field(default_factory=list)


class WebhookSchema(BaseModel):
    id: str
    payload: list[PayloadSchema]


@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def create_entry(secret: SecretStr, webhook_data: WebhookSchema | None = None) -> None:
    """
    Create a time entry from 9AM - 5PM on the day of the leave.
    """

    print(webhook_data)

    # 1. Verify the secret
    if not os.environ.get("WEBHOOK_SECRET") == secret:
        print("Incorrect credentials")
        return

    # 2. Extract User and their date of leave
    print("User and their leave date extracted")

    # 3. Track the time for the user for the date via ClickUp API
    print("Time tracked")
