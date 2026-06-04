from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from . import storage

app = FastAPI(
    title="Jedi Holocron Vault",
    description="Store and retrieve sacred Jedi knowledge — if you can find it.",
)


class Holocron(BaseModel):
    name: str   # SECURITY: not validated for ../ path traversal
    body: str


@app.post("/holocron", status_code=201)
def store(holocron: Holocron):
    try:
        if storage.holocron_exists(holocron.name):
            raise HTTPException(
                status_code=409,
                detail="Holocron already exists. The Force does not allow overwriting."
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        storage.write_holocron(holocron.name, holocron.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"name": holocron.name, "status": "stored"}


@app.get("/holocron/{name}")
def read(name: str):
    try:
        return {"name": name, "body": storage.read_holocron(name)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Holocron not found")
