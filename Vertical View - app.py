import streamlit as st
import requests
import time
import concurrent.futures

st.set_page_config(page_title="LLM Comparison", layout="wide")

# Custom CSS for compact remove buttons and selectbox alignment
st.markdown("""
<style>
.stButton button {
    padding: 0px 5px !important;
    min-width: unset !important;
    font-size: 10px !important;
    height: 20px !important;
    line-height: 1 !important;
    margin-top: 28px !important;
    float: right !important;
    margin-left: 5px !important;
}
div[data-testid="stSelectbox"] {
    width: 100% !important;
}
div[data-testid="stFormSubmitButton"] + div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] {
    align-items: flex-end;
}
/* Style for the "Run Models" button */
button[data-testid="stButton-primary"] {
    background-color: #FF0000 !important; /* Red background */
    color: white !important; /* White text */
    border-radius: 8px !important; /* Rounded corners */
    padding: 10px 20px !important; /* Adjust padding as needed */
    font-size: 16px !important; /* Adjust font size as needed */
}
</style>
""", unsafe_allow_html=True)

# Sidebar for controls
with st.sidebar:
    st.title("LLM Prompt & Models")
    prompt = st.text_area("Prompt", "")

    @st.cache_data
    def get_models():
        try:
            res = requests.get("http://localhost:11434/api/tags").json()
            return [m["name"] for m in res.get("models", [])]
        except Exception as e:
            st.error(f"Could not fetch models from Ollama: {e}")
            return []

    models_available = get_models()

    if not models_available:
        st.warning("No models found. Ensure Ollama is running and has models pulled.")
        st.stop()

    if "model_count" not in st.session_state:
        st.session_state.model_count = 2
    if "selected_models" not in st.session_state:
        st.session_state.selected_models = [""] * st.session_state.model_count

    # Logic to add a new model selection
    if st.button("Add new model"):
        st.session_state.model_count += 1
        st.session_state.selected_models.append("")

    # Display model selection boxes and remove buttons
    for i in range(st.session_state.model_count):
        with st.container():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                # Ensure selected_models list is long enough for the current index
                if i >= len(st.session_state.selected_models):
                    st.session_state.selected_models.append("")

                # Determine the initial selection for the selectbox
                current_selection_index = 0
                if st.session_state.selected_models[i] in models_available:
                    current_selection_index = models_available.index(st.session_state.selected_models[i])
                elif models_available: # If previous selection isn't available, default to first available
                    st.session_state.selected_models[i] = models_available[0]
                    current_selection_index = 0
                
                st.session_state.selected_models[i] = st.selectbox(
                    f"Model {i+1}",
                    models_available,
                    index=current_selection_index,
                    key=f"model_select_{i}"
                )
            with col2:
                if st.button("x", key=f"remove_model_{i}"):
                    if st.session_state.model_count > 1:
                        st.session_state.selected_models.pop(i)
                        st.session_state.model_count -= 1
                        st.rerun() # Rerun to update the UI immediately after removal

    run = st.button("Run Models", type="primary")

# Main display area
st.title("Running LLMs in parallel")

# Function to query a single Ollama model
def query_ollama_model(model_name, prompt_text):
    """Function to query a single Ollama model."""
    try:
        start_time = time.time()
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": prompt_text, "stream": False},
            headers={"Content-Type": "application/json"},
        )
        res.raise_for_status()
        response_data = res.json()
        end_time = time.time()

        duration = round(end_time - start_time, 2)
        content = response_data.get("response", "")
        # Fallback for eval_count if not present, approximate by word count
        eval_count = response_data.get("eval_count", len(content.split())) 
        eval_rate = response_data.get("eval_rate", round(eval_count / duration, 2) if duration > 0 else 0)

        return {
            "model": model_name,
            "duration": duration,
            "eval_count": eval_count,
            "eval_rate": eval_rate,
            "response": content
        }
    except Exception as e:
        return {
            "model": model_name,
            "duration": 0,
            "eval_count": 0,
            "eval_rate": 0,
            "response": f"Error: {e}"
        }

if run and prompt.strip():
    model_inputs = [model for model in st.session_state.selected_models if model]
    
    if not model_inputs:
        st.warning("Please select at least one model to generate a response.")
    else:
        # Create columns dynamically based on the number of selected models
        cols = st.columns(len(model_inputs))
        
        # Use a dictionary to store placeholder containers for each model's output
        model_output_containers = {}

        for i, model in enumerate(model_inputs):
            with cols[i]:
                model_color = "blue" if i % 2 == 0 else "red"
                # Display the model name ONCE at the top of its column
                st.markdown(f"<h3 style='color:{model_color};'>{model}</h3>", unsafe_allow_html=True)
                
                # Create an empty placeholder where the spinner and later the content will live
                model_output_containers[model] = st.empty()
                
                # Show spinner in this container
                with model_output_containers[model].container():
                    st.spinner(f"Running {model}...")


        # Use ThreadPoolExecutor for concurrent execution
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(model_inputs)) as executor:
            # Map models to futures
            future_to_model = {executor.submit(query_ollama_model, model, prompt): model for model in model_inputs}
            
            # As futures complete, update the respective placeholders
            for future in concurrent.futures.as_completed(future_to_model):
                model_name = future_to_model[future]
                result = future.result() # Get the result (either success or error dict)
                all_results.append(result)

                # Update the content of the specific model's container
                # The .empty() call on the container is implicitly handled by writing new content to it.
                with model_output_containers[model_name].container():
                    # No need to re-display model name here, it's already at the top of the column
                    
                    if "Error" in result["response"]:
                        st.error(f"Error: {result['response']}")
                    else:
                        st.markdown(
                            f"""
                            <div style="background-color:#e6f0ff; padding:10px; border-radius:8px; margin-bottom:10px;">
                                <b>Duration</b>: <span style="color:#3366cc;">{result['duration']} secs</span><br>
                                <b>Eval count</b>: <span style="color:green;">{result['eval_count']} tokens</span><br>
                                <b>Eval rate</b>: <span style="color:green;">{result['eval_rate']} tokens/s</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.write(result["response"])
