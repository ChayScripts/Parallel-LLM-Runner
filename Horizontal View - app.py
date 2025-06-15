import streamlit as st
import requests
import time

st.set_page_config(page_title="LLM Comparison", layout="wide")

st.title("Running LLMs in parallel")

# Get available models
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

prompt = st.text_area("Prompt", "")

if "model_count" not in st.session_state:
    st.session_state.model_count = 2
if "selected_models" not in st.session_state:
    st.session_state.selected_models = ["", ""]  # initial 2 models

# Add model dynamically
if st.button("Add new model"):
    st.session_state.model_count += 1
    st.session_state.selected_models.append("")

# Display model selectors
for i in range(st.session_state.model_count):
    st.session_state.selected_models[i] = st.selectbox(
        f"Model {i+1}",
        models_available,
        index=0 if i >= len(st.session_state.selected_models) or not st.session_state.selected_models[i] else models_available.index(st.session_state.selected_models[i]),
        key=f"model_select_{i}"
    )

# Run button
if st.button("Generate") and prompt.strip():
    model_inputs = st.session_state.selected_models
    responses = []

    for model in model_inputs:
        start = time.time()
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            ).json()

            duration = round(time.time() - start, 2)
            content = response.get("response", "").strip()
            eval_count = response.get("eval_count", len(content.split()))
            eval_rate = response.get("eval_rate", round(eval_count / duration, 2))

            responses.append({
                "model": model,
                "duration": duration,
                "eval_count": eval_count,
                "eval_rate": eval_rate,
                "response": content
            })
        except Exception as e:
            responses.append({
                "model": model,
                "duration": 0,
                "eval_count": 0,
                "eval_rate": 0,
                "response": f"Error: {e}"
            })

    cols = st.columns(len(responses))
    for i, res in enumerate(responses):
        with cols[i]:
            st.markdown(f"### {res['model']}")
            st.info(
                f"**Duration**: {res['duration']} secs  \n"
                f"**Eval count**: {res['eval_count']} tokens  \n"
                f"**Eval rate**: {res['eval_rate']} tokens/s"
            )
            st.write(res["response"])
