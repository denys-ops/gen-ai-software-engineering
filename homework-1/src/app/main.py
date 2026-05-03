from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.accounts import router as accounts_router
from app.api.transactions import router as transactions_router

app = FastAPI(title="Banking Transactions API")

app.include_router(transactions_router)
app.include_router(accounts_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = loc[-1] if loc else "body"
        if field == "body":
            field = loc[1] if len(loc) > 1 else "body"
        details.append({"field": str(field), "message": err["msg"]})
    return JSONResponse(
        status_code=400,
        content={"error": "Validation failed", "details": details},
    )
