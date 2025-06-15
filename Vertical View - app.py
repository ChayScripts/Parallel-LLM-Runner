import streamlit as st
import requests
import time

st.set_page_config(page_title="LLM Comparison", layout="wide")

# Sidebar for controls
with st.sidebar:
    st.title("LLM Prompt & Models")
    prompt = st.text_area("Prompt", "")

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

    if "model_count" not in st.session_state:
        st.session_state.model_count = 2
    if "selected_models" not in st.session_state:
        st.session_state.selected_models = ["", ""]

    # Add model dynamically
    if st.button("Add new model"):
        st.session_state.model_count += 1
        st.session_state.selected_models.append("")

    # Model selectors
    for i in range(st.session_state.model_count):
        st.session_state.selected_models[i] = st.selectbox(
            f"Model {i+1}",
            models_available,
            index=0 if not st.session_state.selected_models[i] else models_available.index(st.session_state.selected_models[i]),
            key=f"model_select_{i}"
        )

    run = st.button("Generate")

# Main display area
st.title("Running LLMs in parallel with Ollama")

if run and prompt.strip():
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

    def get_alternating_color(index):
        return "blue" if index % 2 == 0 else "red"

    cols = st.columns(len(responses))
    for i, res in enumerate(responses):
        with cols[i]:
            model_color = get_alternating_color(i)
            st.markdown(
                f"<h3 style='color:{model_color};'>{res['model']}</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div style="background-color:#e6f0ff; padding:10px; border-radius:8px; margin-bottom:10px;">
                    <b>Duration</b>: <span style="color:#3366cc;">{res['duration']} secs</span> &nbsp;
                    <b>Eval count</b>: <span style="color:green;">{res['eval_count']} tokens</span> &nbsp;
                    <b>Eval rate</b>: <span style="color:green;">{res['eval_rate']} tokens/s</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write(res["response"])
