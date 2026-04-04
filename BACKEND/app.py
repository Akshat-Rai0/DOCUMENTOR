from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from model import UserInput, UserOutput
from utils import process_input

app = FastAPI(
    title="Documentor API", 
    description="Provides backend logic for user input processing."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Specify frontend url in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Documentor API!"}

@app.post("/api/process", response_model=UserOutput)
async def handle_user_input(user_input: UserInput):
    """
    Endpoint to receive and process user input.
    """
    try:
        # Pass logic to the utility function
        result = process_input(user_input.content)
        return UserOutput(processed_content=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
