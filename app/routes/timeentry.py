from fastapi import APIRouter
from fastapi import status
from pydantic import Field, SecretStr, BaseModel
import os
import aiohttp
from datetime import datetime
import pytz
import base64
import boto3
import json


dynamodb_client = boto3.client('dynamodb', region_name=os.environ.get("DYNAMO_DB_REGION"))
router = APIRouter(tags=["Time Entries"], prefix="/time_entries")


class AssigneeSchema(BaseModel):
    id: int

class PayloadSchema(BaseModel):
    id: str
    name: str
    assignees: list[AssigneeSchema] = Field(default_factory=list)
    custom_fields: list[dict] = Field(default_factory=list)


class WebhookSchema(BaseModel):
    id: str
    payload: PayloadSchema


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def create_entry(secret: SecretStr, webhook_data: WebhookSchema) -> None:
    """
    Create a time entry from 9AM - 5PM on the day of the leave.
    """

    # 1. Verify the secret
    if os.environ.get("WEBHOOK_SECRET") != secret.get_secret_value():
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
                round(datetime.fromtimestamp(int(field["value"])/1000, pytz.timezone("Asia/Karachi")).replace(hour=9, minute=0).timestamp() * 1000)
            )
    if not leave_for:
        return
    task_id = webhook_data.payload.id
    assignee = webhook_data.payload.assignees[0].id
    leave_reason = webhook_data.payload.name

    print("User and their leave date extracted")

    # 3. Track the time for the user for the date via ClickUp API
    async with aiohttp.ClientSession() as clickup_session:
        async with clickup_session.post(
                f"https://api.clickup.com/api/v2/team/{os.environ.get("CLICKUP_TEAM_ID")}/time_entries",
                json={
                    "description": "Marked as leave via the API",
                    "start": leave_for,
                    "billable": True,
                    "duration": os.environ.get("CLICKUP_DURATION_TO_TRACK"),
                    "assignee": assignee,
                    "tid": task_id
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": os.environ.get("CLICKUP_API_KEY")
                }
        ) as resp:
            print(resp.status, " --> ", await resp.text())

    async with aiohttp.ClientSession() as allhours_session:
        async with allhours_session.post(
            "https://login.spica.com/connect/token",
            data=b"grant_type=client_credentials&scope=api",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {base64.urlsafe_b64encode(f"{os.environ.get('ALLHOURS_CLIENT_ID')}:{os.environ.get('ALLHOURS_CLIENT_SECRET')}".encode('ascii')).decode('utf-8')}"
            }
        ) as token_resp:
            authentication_info = json.loads(await token_resp.text())
            auth_header = f"{authentication_info["token_type"]} {authentication_info["access_token"]}"
            allhours_user_id = dynamodb_client.get_item(
                TableName=os.environ.get("DYNAMO_DB_TABLE"),
                Key={
                    'clickupId': {
                        'N': str(assignee)
                    }
                }
            )["Item"]["allhoursId"]["S"]

            async with allhours_session.post(
                "https://api4.allhours.com/api/v1/Absences",
                json={
                  "UserId": allhours_user_id,
                  "Timestamp": datetime.fromtimestamp(leave_for/1000, pytz.timezone("Asia/Karachi")).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                  "AbsenceDefinitionId": os.environ.get("ALLHOURS_ABSENCE_DEFINITION_TYPE_ID"),
                  "Origin": 2,
                  "Comment": leave_reason,
                  "IsPartial": False,
                  "OverrideHolidayAbsence": False
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": auth_header
                }
            ) as resp:
                print(resp.status)
