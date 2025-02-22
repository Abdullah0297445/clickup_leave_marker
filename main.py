import requests
import pytz
from datetime import datetime
import os
import json
from pydantic import Field, BaseModel


class AssigneeSchema(BaseModel):
    id: int
    username: str


class PayloadSchema(BaseModel):
    id: str
    name: str
    assignees: list[AssigneeSchema] = Field(default_factory=lambda: list)
    custom_fields: list[dict] = Field(default_factory=lambda: list)


class WebhookSchema(BaseModel):
    id: str
    payload: PayloadSchema


def handler(event, context):
    """
    Create a time entry from 9AM - 5PM on the day of the leave.
    """
    print("INFO: Incoming event data: \n\n", event)

    try:
        if os.environ.get("WEBHOOK_SECRET") != event["queryStringParameters"]["secret"]:
            print("Incorrect credentials")
            return
    except KeyError:
        print("Error: Webhook secret was not included in the request.")
        return

    try:
        webhook_data: WebhookSchema = WebhookSchema(**json.loads(event["body"]))
    except KeyError:
        print("Error: Invalid request body.")
        return

    if not webhook_data.payload.assignees or not webhook_data.payload.custom_fields:
        return

    try:
        name, val = os.environ["LEAVE_DATE_VAR_VAL_PAIR"].split("=")
    except KeyError:
        return

    task_id = webhook_data.payload.id
    assignee = webhook_data.payload.assignees[0].id

    print(f"INFO: Processing the leave of {webhook_data.payload.assignees[0].username.capitalize()}")

    leave_for = None
    for field in webhook_data.payload.custom_fields:
        if field[name] == val:
            # Dividing and multiplying by thousand since the timestamp should be in milliseconds
            leave_for = int(
                round(
                    datetime.fromtimestamp(
                        int(field["value"]) / 1000,
                        pytz.timezone("Asia/Karachi")
                    ).replace(hour=9, minute=0).timestamp() * 1000
                )
            )
    if not leave_for:
        print("WARN: The date leave is applied for is empty; returing.")
        return

    print("INFO: ID of the user and their applied leave date extracted.")

    requests.post(
        f"https://api.clickup.com/api/v2/team/{os.environ.get("CLICKUP_TEAM_ID")}/time_entries",
        json={
            "description": f"Marked as leave via the API. Reason: {webhook_data.payload.name}",
            "start": leave_for,
            "billable": False,
            "duration": os.environ.get("CLICKUP_DURATION_TO_TRACK"),
            "assignee": assignee,
            "tid": task_id
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": os.environ.get("CLICKUP_API_KEY")
        }
    )

    print("INFO: Successfully tracked time for the applied leave.")

    return {
        "statusCode": 204,
        "headers": {
            "Content-Type": "application/json",
        },
        "isBase64Encoded": False
    }
