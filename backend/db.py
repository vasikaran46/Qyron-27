from functools import lru_cache

from fastapi import HTTPException
from supabase import Client, create_client

from backend.config import settings


@lru_cache
def service_client() -> Client:
    config = settings()
    if not config.supabase_url or not config.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured on this server.")
    return create_client(config.supabase_url, config.supabase_service_role_key)


def auth_client() -> Client:
    config = settings()
    if not config.supabase_url or not config.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured on this server.")
    return create_client(config.supabase_url, config.supabase_anon_key)
