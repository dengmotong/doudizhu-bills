from fastapi import APIRouter

from .. import database

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/cumulative")
def cumulative():
    return database.get_player_cumulative_stats()


@router.get("/monthly")
def monthly():
    return database.get_player_stats_by_month()


@router.get("/daily")
def daily():
    return database.get_player_stats_by_day()


@router.get("/session")
def by_session():
    return database.get_player_stats_by_session()
