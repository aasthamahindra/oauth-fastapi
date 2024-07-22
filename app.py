# start point to create a web API
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from controllers.UserController import user_controller_router

app = FastAPI()

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

app.include_router(user_controller_router, prefix='/users', tags=['Users'])

# enable CORS middleware to allow requests from different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == 'main':
    uvicorn.run("app:app",host=os.environ.get("HOST"), port=int(os.environ.get("PORT")), reload=True)
