from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.timeentry import router as TimeEntryRouter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(TimeEntryRouter, tags=["Time Entries"], prefix="/time_entries")
