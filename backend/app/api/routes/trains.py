import time

from fastapi import APIRouter, Depends
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.train import TrainsSnapshotResponse
from app.services.train_service import load_trains_snapshot

router = APIRouter(tags=["trains"])


@router.get("/api/trains", response_model=TrainsSnapshotResponse)
def get_trains(driver: Driver = Depends(get_driver)):
	return TrainsSnapshotResponse(trains=load_trains_snapshot(driver), timestamp=time.time())
