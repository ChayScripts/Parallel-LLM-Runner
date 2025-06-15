import streamlit as st
import requests
import time

st.set_page_config(page_title="LLM Comparison", layout="wide")

st.markdown("""
<style>
.stButton button {
    padding: 0px 5px !important;
    min-width: unset !important;
    font-size: 10px !important;
    height: 25px !important;
    line-height: 1 !important;
    margin-top: 28px !important;
}
div[data-testid="stSelectbox"] > div {
    margin-right: 0px !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Running LLMs in parallel")

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
    st.session_state.selected_models = ["", ""]

def remove_model(index):
    if st.session_state.model_count > 1:
        st.session_state.model_count -= 1
        st.session_state.selected_models.pop(index)

for i in range(st.session_state.model_count):
    col1, col2 = st.columns([0.97, 0.02]) 
    with col1:
        st.session_state.selected_models[i] = st.selectbox(
            f"Model {i+1}",
            models_available,
            index=0 if i >= len(st.session_state.selected_models) or not st.session_state.selected_models[i] else models_available.index(st.session_state.selected_models[i]),
            key=f"model_select_{i}"
        )
    with col2:
        st.button("✖", key=f"remove_model_{i}", on_click=remove_model, args=(i,))

selected_models_filtered = [model for model in st.session_state.selected_models if model]

_, _, spacer, col_add, col_run = st.columns([0.5, 0.2, 0.1, 0.1, 0.1])
with col_add:
    if st.button("Add new model"):
        st.session_state.model_count += 1
        st.session_state.selected_models.append("")
        st.rerun()
with col_run:
    run_clicked = st.button("Run Models", type="primary")

if run_clicked and prompt and selected_models_filtered:
    responses = []

    response_placeholders = [st.empty() for _ in selected_models_filtered]

    for i, model in enumerate(selected_models_filtered):
        try:
            with st.spinner(f"Running {model}..."):
                start_time = time.time()
                res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    headers={"Content-Type": "application/json"},
                )
                res.raise_for_status()
                response_data = res.json()
                end_time = time.time()

            duration = round(end_time - start_time, 2)
            content = response_data.get("response", "")
            eval_count = response_data.get("eval_count", len(content.split()))
            eval_rate = response_data.get("eval_rate", round(eval_count / duration, 2))

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
            st.markdown(
                f"### <span style='color:#3366cc'>{res['model']}</span>" if i % 2 == 0 else f"### <span style='color:#cc0000'>{res['model']}</span>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div style="background-color:#e6f0ff; padding:10px; border-radius:8px; margin-bottom:10px;">
                    <b>Duration</b>: <span style="color:#3366cc;">{res['duration']} secs</span> &nbsp;
                    <b>Eval count</b>: <span style="color:green;">{res['eval_count']} tokens</span> &nbsp;
                    <b>Eval rate</b>: <span style="color:green;">{res['eval_rate']} tokens/s</span>
                </div>
                """, unsafe_allow_html=True
            )
            st.write(res["response"])
