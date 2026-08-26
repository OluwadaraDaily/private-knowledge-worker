from fastapi import APIRouter
from pydantic import BaseModel


class ApiInfo(BaseModel):
    name: str
    version: str


api_router = APIRouter()


@api_router.get("/", response_model=ApiInfo, summary="Get API information")
async def get_api_info() -> ApiInfo:
    return ApiInfo(
        name="Private Knowledge Worker API",
        version="0.1.0",
    )
