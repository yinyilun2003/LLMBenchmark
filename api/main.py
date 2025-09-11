import uvicorn
from fastapi import FastAPI
from routers import auth, user, task, runs, metrics, reports, datasets, adapters, webhooks, health, admin, log

app = FastAPI(title="LLM Benchmark API", version="1.0")

API_V1 = "/routers/v1"
for r in [health, auth, user, task, runs, metrics, reports, datasets, adapters, webhooks, admin, log]:
    app.include_router(r.router, prefix=API_V1)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)