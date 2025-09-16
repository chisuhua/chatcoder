#!/bin/bash

# run_dev_workflow.sh
# Simulates a complete AI-assisted development workflow using the chatcoder CLI.

set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting AI-Assisted Development Workflow Simulation..."

# --- Configuration ---
PROJECT_NAME="SimulatedTestProject"
FEATURE_DESCRIPTION="Implement a basic user authentication API"
WORKFLOW_NAME="default" # Must match an available workflow schema
TEMP_DIR=$(mktemp -d) # Create a temporary directory for simulation
SIMULATION_DIR="$TEMP_DIR/$PROJECT_NAME"
RESPONSE_DIR="$TEMP_DIR/responses"
FEATURE_ID=""
INSTANCE_ID=""

# Cleanup function to remove temporary files on exit
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    echo "✅ Cleanup complete."
}
trap cleanup EXIT

# --- Setup Simulation Environment ---
echo "🏗️  Setting up simulation environment in $SIMULATION_DIR..."
mkdir -p "$SIMULATION_DIR"
cd "$SIMULATION_DIR"

# Initialize a minimal Python project structure for context detection
mkdir -p src tests
echo "print('Hello, Simulated World!')" > src/main.py
echo "fastapi" > requirements.txt
echo "# $PROJECT_NAME" > README.md

echo "📄 Initializing ChatCoder project..."
chatcoder init <<EOF
python
cli
$PROJECT_NAME
FastAPI-based CLI tool
pytest
black
EOF

# Verify initialization
if [[ ! -d ".chatcoder" ]]; then
    echo "❌ Error: .chatcoder directory was not created."
    exit 1
fi

echo "✅ Project initialized."

# --- Step 1: Start New Feature ---
echo "🆕 Starting new feature: '$FEATURE_DESCRIPTION'..."
START_OUTPUT=$(chatcoder feature start --description "$FEATURE_DESCRIPTION" --workflow "$WORKFLOW_NAME")
echo "$START_OUTPUT"

# Extract FEATURE_ID (assuming it's on a line like "Feature ID: feat_...")
# This uses grep and sed, adjust regex if output format changes
FEATURE_ID=$(echo "$START_OUTPUT" | grep -oE 'Feature ID: feat_[a-zA-Z0-9_]+' | head -n 1 | cut -d' ' -f3)
if [[ -z "$FEATURE_ID" ]]; then
    echo "❌ Error: Could not extract FEATURE_ID from start output."
    echo "$START_OUTPUT"
    exit 1
fi
echo "🔑 Feature ID assigned: $FEATURE_ID"

# --- Step 2: Get Prompt for Current Task (Analyze Phase) ---
echo "🧾 Generating prompt for Analyze phase..."
mkdir -p "$RESPONSE_DIR"
PROMPT_FILE="$RESPONSE_DIR/${FEATURE_ID}_analyze_prompt.md"
chatcoder feature task prompt "$FEATURE_ID" > "$PROMPT_FILE"

if [[ ! -s "$PROMPT_FILE" ]]; then
    echo "❌ Error: Prompt file for Analyze phase is empty or was not created."
    exit 1
fi
echo "✅ Analyze prompt generated: $PROMPT_FILE"

# --- Step 3: Simulate AI Response (Create dummy analyze response) ---
echo "🤖 Simulating AI response for Analyze phase..."
ANALYZE_RESPONSE_FILE="$RESPONSE_DIR/${FEATURE_ID}_analyze_response.md"
cat > "$ANALYZE_RESPONSE_FILE" <<EOF
## Analysis Summary

The user wants to implement a basic user authentication API. This involves designing endpoints for user registration, login, and potentially logout. Security considerations like password hashing and token management (e.g., JWT) are crucial.

## Proposed Plan

1.  Define User model/schema.
2.  Implement user registration endpoint (/register).
3.  Implement user login endpoint (/login) with JWT token generation.
4.  Secure other endpoints using the JWT middleware.

## Changes
### File: src/models.py
\`\`\`python
from pydantic import BaseModel

class User(BaseModel):
    username: str
    email: str
    # Password will be hashed, not stored directly
    # hashed_password will be added by the service layer

class UserCreate(User):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
\`\`\`
Description: Define Pydantic models for User, UserCreate, Token, and TokenData.

### File: src/auth.py
\`\`\`python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from src.models import User, UserCreate, Token, TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration (use environment variables in practice)
SECRET_KEY = "your-super-secret-key" # Don't put secrets in code!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
\`\`\`
Description: Implement password hashing utilities and JWT token creation logic.
EOF
echo "✅ Simulated AI analyze response created: $ANALYZE_RESPONSE_FILE"

# --- Step 4: Apply Analyze Response ---
echo "💾 Applying simulated AI analyze response..."
chatcoder feature task apply "$FEATURE_ID" "$ANALYZE_RESPONSE_FILE"
echo "✅ Analyze response applied."

# --- Step 5: Confirm Analyze Task and Advance ---
echo "✅ Confirming Analyze task completion..."
SUMMARY="Analyzed requirements and planned the auth API structure. Created models and auth utility stubs."
chatcoder feature task confirm "$FEATURE_ID" --summary "$SUMMARY"
echo "✅ Analyze task confirmed and workflow advanced."

# --- Step 6: Get Prompt for Next Task (Design/Implement Phase) ---
# Assuming workflow advances to the next logical phase automatically
echo "🧾 Generating prompt for next phase (likely Design/Implement)..."
NEXT_PROMPT_FILE="$RESPONSE_DIR/${FEATURE_ID}_next_prompt.md"
chatcoder feature task prompt "$FEATURE_ID" > "$NEXT_PROMPT_FILE"

if [[ ! -s "$NEXT_PROMPT_FILE" ]]; then
    echo "⚠️  Warning: Prompt file for next phase is empty or was not created. Might be at the end of the workflow."
    # Don't exit on this, as the workflow might be complete
else
    echo "✅ Next phase prompt generated: $NEXT_PROMPT_FILE"
fi

# --- Step 7: Simulate AI Response for Next Task (Implement/Register Endpoint) ---
echo "🤖 Simulating AI response for implementing Register endpoint..."
REGISTER_RESPONSE_FILE="$RESPONSE_DIR/${FEATURE_ID}_register_response.md"
cat > "$REGISTER_RESPONSE_FILE" <<EOF
## Implementation Summary

Implementing the user registration endpoint.

## Changes
### File: src/database.py
\`\`\`python
# Dummy in-memory storage for simulation
# In a real app, use a proper database (SQLAlchemy, MongoDB, etc.)
fake_users_db = {}
\`\`\`
Description: Create a dummy database storage.

### File: src/main.py
\`\`\`python
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from src.models import User, UserCreate, Token, TokenData
from src.auth import get_password_hash, create_access_token, verify_password, pwd_context
from src.database import fake_users_db # Import dummy DB
from datetime import timedelta
from typing import Annotated

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/register", response_model=User)
async def register_user(user: UserCreate):
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    hashed_password = get_password_hash(user.password)
    # Store user without plain password
    db_user = User(username=user.username, email=user.email)
    fake_users_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password
    }
    return db_user

# Placeholder for login endpoint
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = User(**user_dict)
    if not verify_password(form_data.password, user_dict["hashed_password"]):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30) # Use constant
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency to get current user (stub)
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = fake_users_db.get(token_data.username)
    if user is None:
        raise credentials_exception
    return User(**user)

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

\`\`\`
Description: Implement the /register endpoint, a placeholder /token endpoint, and a dependency to get the current user.
EOF
echo "✅ Simulated AI register endpoint response created: $REGISTER_RESPONSE_FILE"

# --- Step 8: Apply Register Endpoint Response ---
echo "💾 Applying simulated AI register endpoint response..."
chatcoder feature task apply "$FEATURE_ID" "$REGISTER_RESPONSE_FILE"
echo "✅ Register endpoint response applied."

# --- Step 9: Confirm Register Task and Advance ---
echo "✅ Confirming Register task completion..."
SUMMARY_REG="Implemented user registration endpoint with password hashing and dummy DB storage. Added placeholder login/token endpoint."
chatcoder feature task confirm "$FEATURE_ID" --summary "$SUMMARY_REG"
echo "✅ Register task confirmed and workflow advanced."

# --- Step 10: Final Status Check ---
echo "📊 Checking final feature status..."
FINAL_STATUS_FILE="$RESPONSE_DIR/${FEATURE_ID}_final_status.json"
chatcoder feature status "$FEATURE_ID" > "$FINAL_STATUS_FILE"
echo "✅ Final feature status captured: $FINAL_STATUS_FILE"

# --- Completion ---
echo "🎉 Simulated AI-Assisted Development Workflow Completed!"
echo "📁 Temporary project and outputs were in: $SIMULATION_DIR (cleaned up on script exit unless interrupted)"
echo "📄 Simulated AI responses and prompts are in: $RESPONSE_DIR (cleaned up on script exit unless interrupted)"
echo "💡 Review the generated files in the temporary project directory to see the results!"

# Note: The temporary directory and its contents will be deleted when the script exits due to the 'trap' command.
# To inspect the results, comment out the 'trap cleanup EXIT' line and the 'cleanup' function call.
