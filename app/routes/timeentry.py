from fastapi import APIRouter
from fastapi import status
from pydantic import Field, SecretStr, BaseModel
import os
import aiohttp
from datetime import datetime


router = APIRouter()


class AssigneeSchema(BaseModel):
    id: int

class PayloadSchema(BaseModel):
    id: str
    assignees: list[AssigneeSchema] = Field(default_factory=list)
    custom_fields: list[dict] = Field(default_factory=list)


class WebhookSchema(BaseModel):
    id: str
    payload: PayloadSchema


@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def create_entry(secret: SecretStr, webhook_data: WebhookSchema) -> None:
    """
    Create a time entry from 9AM - 5PM on the day of the leave.
    """

    # 1. Verify the secret
    if not os.environ.get("WEBHOOK_SECRET") == secret:
        print("Incorrect credentials")
        return

    # 2. Extract User and their date of leave
    if not webhook_data.payload.assignees or not webhook_data.payload.custom_fields:
        return

    try:
        name, val = os.environ["LEAVE_DATE_VAR_VAL_PAIR"].split("=")
    except KeyError:
        return

    leave_for = None
    for field in webhook_data.payload.custom_fields:
        if field[name] == val:
            # Dividing and multiplying by thousand since the timestamp should be in milliseconds
            leave_for = int(
                round(datetime.fromtimestamp(int(field["value"])/1000).replace(hour=9, minute=0).timestamp() * 1000)
            )
    if not leave_for:
        return
    task_id = webhook_data.payload.id
    assignee = webhook_data.payload.assignees[0].id

    print("User and their leave date extracted")

    # 3. Track the time for the user for the date via ClickUp API
    try:
        team_id = os.environ["CLICKUP_TEAM_ID"]
    except KeyError:
        return

    try:
        api_key = os.environ["CLICKUP_API_KEY"]
    except KeyError:
        return

    try:
        duration = os.environ["CLICKUP_DURATION_TO_TRACK"]
    except KeyError:
        return

    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"https://api.clickup.com/api/v2/team/{team_id}/time_entries",
                json={
                    "description": "Marked as leave via the API",
                    "start": leave_for,
                    "billable": True,
                    "duration": duration,
                    "assignee": assignee,
                    "tid": task_id
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": api_key
                }
        ) as resp:
            print(resp.status_code, " --> ", await resp.text())
