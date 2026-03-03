from fastapi import FastAPI

app = FastAPI(title="ForensicEdge API")

@app.get("/")
def root():
    return {"message": "ForensicEdge Backend Running"}