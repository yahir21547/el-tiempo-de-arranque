"""Actualización permanente opcional del XLSX mediante un commit de GitHub.

NUNCA exponer el token al navegador: solo se lee en el servidor con secretos.
Requiere también contraseña administrativa; usuarios comunes no pueden reemplazar
la base por el simple hecho de subir un archivo.
"""
from __future__ import annotations
import base64
import hmac
import os
from urllib.parse import quote
import requests

from services.resources import EXCEL_NAME


class PersistenceError(RuntimeError):
    pass


def github_settings(secrets: dict) -> dict | None:
    get=lambda name,default="": str(secrets.get(name,os.environ.get(name,default))).strip()
    cfg={"token":get("GITHUB_TOKEN"),"repo":get("GITHUB_REPO"),
         "branch":get("GITHUB_BRANCH","main"),"password":get("ADMIN_PASSWORD")}
    return cfg if cfg["token"] and cfg["repo"] and cfg["password"] else None


def validate_admin(candidate: str, cfg: dict) -> bool:
    return bool(candidate and cfg.get("password") and hmac.compare_digest(candidate,cfg["password"]))


def persist_to_github(contents: bytes, cfg: dict, uploaded_filename: str) -> str:
    """Reemplaza el XLSX de data/ manteniendo ruta estable para el repositorio nuevo."""
    if not cfg or not cfg.get("repo") or "/" not in cfg["repo"]:
        raise PersistenceError("Configure GITHUB_REPO como owner/repo.")
    path="data/"+EXCEL_NAME
    endpoint="https://api.github.com/repos/"+cfg["repo"]+"/contents/"+quote(path)
    headers={"Authorization":"Bearer "+cfg["token"],"Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28"}
    try:
        response=requests.get(endpoint,headers=headers,params={"ref":cfg["branch"]},timeout=30)
        if response.status_code == 404:
            sha=None  # Puede ser una creación inicial.
        else:
            response.raise_for_status()
            sha=response.json().get("sha")
        payload={"message":f"Actualizar base de motores: {uploaded_filename}",
                 "content":base64.b64encode(contents).decode("ascii"),"branch":cfg["branch"]}
        if sha:payload["sha"]=sha
        put=requests.put(endpoint,headers=headers,json=payload,timeout=65)
        if put.status_code not in (200,201):
            raise PersistenceError(f"GitHub rechazó la actualización ({put.status_code}): {put.text[:450]}")
        return put.json().get("commit",{}).get("html_url","")
    except (requests.RequestException, ValueError) as exc:
        raise PersistenceError(str(exc)) from exc
