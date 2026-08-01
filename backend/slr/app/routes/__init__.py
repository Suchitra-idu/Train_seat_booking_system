"""Aggregate every route group into one router the app mounts."""

from __future__ import annotations

from fastapi import APIRouter

from slr.app.routes import admin, bookings, stream, trips, waitlist

api_router = APIRouter()
api_router.include_router(trips.router)
api_router.include_router(bookings.router)
api_router.include_router(waitlist.router)
api_router.include_router(stream.router)
api_router.include_router(admin.router)
