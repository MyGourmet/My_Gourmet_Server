# Third Party Library
from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from firebase_admin import credentials, initialize_app  # type: ignore

# First Party Library
from api.routers import router  # type: ignore

initialize_app(credentials.Certificate("/auth/service_account.json"))

app = FastAPI()
app.include_router(router.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
