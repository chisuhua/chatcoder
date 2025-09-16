#!/bin/bash

# run_basic_workflow.sh
# Demonstrates a basic AI-assisted workflow using the chatcoder CLI.

set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting Basic ChatCoder Workflow Demo..."

# --- Configuration ---
FEATURE_DESCRIPTION="Add a health check endpoint to the API"
WORKFLOW_NAME="default" # Use the default workflow

# --- Step 1: Start a New Feature ---
echo "1️⃣  Starting new feature: '$FEATURE_DESCRIPTION'"
START_OUTPUT=$(chatcoder feature start --description "$FEATURE_DESCRIPTION" --workflow "$WORKFLOW_NAME")
echo "$START_OUTPUT"

# Extract FEATURE_ID from the output (assuming consistent format)
# This uses grep and sed; adjust regex if Thinker's output format changes.
# Looking for a line like "Feature ID: feat_add_health_check_endpoint"
FEATURE_ID=$(echo "$START_OUTPUT" | grep -oE 'Feature ID: feat_[a-zA-Z0-9_]+' | head -n 1 | cut -d' ' -f3)

if [[ -z "$FEATURE_ID" ]]; then
    echo "❌ Error: Could not extract FEATURE_ID from start output."
    echo "$START_OUTPUT"
    exit 1
fi
echo "   ✅ Feature ID assigned: $FEATURE_ID"

# Get the initial active instance ID for subsequent commands
INITIAL_INSTANCE_ID=$(chatcoder feature status "$FEATURE_ID" | grep -oE 'Instance ID: wfi_[a-zA-Z0-9_]+' | head -n 1 | cut -d' ' -f3)
echo "   🆔 Initial Workflow Instance ID: $INITIAL_INSTANCE_ID"

# --- Step 2: Generate Prompt for the First Task (e.g., Analyze) ---
echo "2️⃣  Generating prompt for the initial task of feature '$FEATURE_ID'..."
PROMPT=$(chatcoder task prompt --feature "$FEATURE_ID")
echo "   📄 Prompt generated:"
echo "----------------------------------------------------------------------"
echo "$PROMPT"
echo "----------------------------------------------------------------------"

# --- Intermission: Simulate AI Interaction ---
echo "🤖 (Simulation) Please provide the AI with the prompt above."
echo "   (Simulation) Assume the AI analyzes the request and responds."
echo "   (Simulation) Save the AI's response (e.g., analysis summary) to a file named 'ai_analysis_response.txt'."
# In a real scenario, you would copy the prompt, send it to an LLM, and get the response.
# For this demo, we create a dummy file.
cat > ai_analysis_response.txt <<EOF
Analyzed the requirement to add a health check endpoint. This is a standard practice for monitoring API availability. The endpoint should return a simple 200 OK status.
EOF
echo "   ✅ (Simulation) Dummy AI analysis response saved to 'ai_analysis_response.txt'."

# --- Step 3: Confirm the Analysis Task ---
echo "3️⃣  Confirming the analysis task for feature '$FEATURE_ID' with AI summary..."
# Pass the content of the dummy response file as the summary
SUMMARY_CONTENT=$(cat ai_analysis_response.txt)
CONFIRM_OUTPUT=$(chatcoder task confirm --feature "$FEATURE_ID" --summary "$SUMMARY_CONTENT")
echo "$CONFIRM_OUTPUT"
echo "   ✅ Analysis task confirmed."

# --- Step 4: Generate Prompt for the Next Task (e.g., Design/Implementation) ---
echo "4️⃣  Generating prompt for the next task (e.g., implementation) of feature '$FEATURE_ID'..."
NEXT_PROMPT=$(chatcoder task prompt --feature "$FEATURE_ID")
echo "   📄 Next task prompt generated:"
echo "----------------------------------------------------------------------"
echo "$NEXT_PROMPT"
echo "----------------------------------------------------------------------"

# --- Intermission: Simulate AI Interaction Again ---
echo "🤖 (Simulation) Please provide the second prompt to the AI."
echo "   (Simulation) Assume the AI designs/implements the endpoint and responds with code/files."
echo "   (Simulation) Save the AI's detailed response (containing file changes) to 'ai_implementation_response.txt'."
# Create a dummy implementation response simulating file creation/modification
cat > ai_implementation_response.txt <<EOF
## Changes
### File: src/main.py
\`\`\`python
from fastapi import FastAPI

app = FastAPI()

# ... existing code ...

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

\`\`\`
Description: Added a GET /health endpoint that returns a JSON status.
EOF
echo "   ✅ (Simulation) Dummy AI implementation response saved to 'ai_implementation_response.txt'."

# --- Step 5: Apply the AI's Implementation ---
echo "5️⃣  Applying the AI-generated implementation for feature '$FEATURE_ID'..."
APPLY_OUTPUT=$(chatcoder task apply --feature "$FEATURE_ID" ai_implementation_response.txt)
echo "$APPLY_OUTPUT"
echo "   ✅ AI implementation applied to the project files."

# --- Step 6: Confirm the Implementation Task ---
echo "6️⃣  Confirming the implementation task for feature '$FEATURE_ID'..."
CONFIRM_IMPL_OUTPUT=$(chatcoder task confirm --feature "$FEATURE_ID" --summary "Implemented the /health endpoint as designed by the AI.")
echo "$CONFIRM_IMPL_OUTPUT"
echo "   ✅ Implementation task confirmed."

# --- Final Status Check ---
echo "7️⃣  Checking final status for feature '$FEATURE_ID'..."
FINAL_STATUS=$(chatcoder feature status "$FEATURE_ID")
echo "   📊 Final Feature Status:"
echo "$FINAL_STATUS"

# --- Completion ---
echo "🎉 Basic ChatCoder Workflow Demo Completed!"
echo "   You have initiated a feature, interacted with AI prompts twice, applied changes, and confirmed tasks."
echo "   Check your project files (e.g., src/main.py) for the added /health endpoint."
echo "   Check the .chatcoder/workflow_instances directory for the workflow state files."
