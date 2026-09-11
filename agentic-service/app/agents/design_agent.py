import uuid
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.workflow_state import WorkflowState
from app.schemas.design_result import DesignResult

# Initialize the LLM 
# Using a model that heavily supports structured output is highly recommended.
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2)

def design_node(state: WorkflowState) -> WorkflowState:
    print(f"[Design Agent] Generating architectural layout for workflow {state.workflow_id}...")
    
    # 1. Gather constraints from previous agents/inputs
    budget = state.input_data.budget_lkr
    land_size = state.input_data.land_size_perches
    preferences = state.input_data.preferences
    
    # Terrain comes from Land Analysis Agent (or manual input)
    terrain = state.terrain_result.get("terrain_type", "flat") if state.terrain_result else "flat"
    
    # 2. Build the System Prompt
    system_message = """
    You are an expert architectural layout generator.
    Your job is to generate a realistic 2D floor plan layout in strict JSON format.
    
    Constraints:
    - Land Size: {land_size} perches (1 perch = 272.25 sqft). DO NOT exceed 65% coverage ratio.
    - Terrain: {terrain}. If 'hillside', foundation must be 'terraced'. If 'flat', use 'slab'.
    - Required Bedrooms: {bedrooms}
    - Required Floors: {floors}
    - Style: {style}
    
    Coordinate System:
    - x, y represents the bottom-left corner of the room in a shared 2D grid (feet).
    - Rooms must not overlap.
    """
    
    # 3. Handle iterative chat-based revisions
    # If the user rejected a previous design and sent a chat prompt, include it.
    user_message = "Generate the initial house design."
    if state.user_revision_prompt:
        user_message = (
            f"The user rejected the previous design and provided this feedback via chat: "
            f"'{state.user_revision_prompt}'\n"
            f"Here is the previous design you made: {json.dumps(state.design_result)}\n"
            f"Please adjust the design to incorporate the user's feedback while maintaining constraints."
        )
    else:
        # If the Validation agent rejected it (automated check failure)
        if state.status == "rejected" and state.validation_result:
            user_message = (
                f"Your previous design failed automated validation: {state.validation_result['reason']}. "
                f"Please fix the layout."
            )

    # 4. Invoke the LLM with structured output
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "{input}")
    ])
    
    structured_llm = llm.with_structured_output(DesignResult)
    chain = prompt | structured_llm
    
    try:
        # Execute AI generation
        result: DesignResult = chain.invoke({
            "land_size": land_size,
            "terrain": terrain,
            "bedrooms": preferences.get("bedrooms", 3),
            "floors": preferences.get("floors", 1),
            "style": preferences.get("style", "modern"),
            "input": user_message
        })
        
        # Save result to state
        # Ensure a fresh design ID is generated if this is a new layout
        result.design_id = str(uuid.uuid4())
        state.design_result = result.model_dump()
        
        # Clear the revision prompt now that it has been handled
        state.user_revision_prompt = None
        
        # Route to Cost Estimation next
        state.current_agent = "cost_estimation"
        
        # Log success
        state.execution_log.append({
            "agent_name": "DesignAgent",
            "action": "Generated layout",
            "result": "success",
            "created_at_utc": "now"
        })
        
        # Send the updated state back to ASP.NET Core
        try:
            import requests
            headers={"X-Internal-API-Key":"shared-internal-secret"}
            update_payload={
                "DesignResult": state.design_result
            }
            requests.patch(
                f"http://localhost:5265/api/v1/internal/workflows/{state.workflow_id}/state",
                json=update_payload,
                headers=headers,
                timeout=5
            )
        except Exception as e:
            print(f"Failed to save design result to ASP.NET Core: {e}")
        
    except Exception as e:
        print(f"Error in Design Agent: {e}")
        state.status = "failed"
        
    return state