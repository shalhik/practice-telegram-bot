from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.post("/webhook/clickup")
async def clickup_webhook(request: Request):
    body = await request.json()
    print(json.dumps(body, indent=2))
    return {"ok": True}