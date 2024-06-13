import mangum
from app.app import app

handler = mangum(app, lifespan="off")
