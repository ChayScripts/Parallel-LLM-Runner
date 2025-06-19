import streamlit as st
import requests
import time
import concurrent.futures
import json
import os
import re

st.set_page_config(page_title="LLM Comparison", layout="wide")

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


button[data-testid="stButton-primary"] {
    background-color: #FF0000 !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-size: 16px !important;
}

.stColumns > div > div > .stButton {
    text-align: left !important;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("LLM Prompt & Models")
    prompt = st.text_area("Prompt", key="sidebar_prompt")

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

    if st.button("Add new model"):
        st.session_state.model_count += 1
        st.session_state.selected_models.append("")

    for i in range(st.session_state.model_count):
        cols = st.columns([0.9, 0.1])
        with cols[0]:
            if i >= len(st.session_state.selected_models):
                st.session_state.selected_models.append("")

            current_selection_index = 0
            if st.session_state.selected_models[i] in models_available:
                current_selection_index = models_available.index(st.session_state.selected_models[i])
            elif models_available:
                st.session_state.selected_models[i] = models_available[0]
                current_selection_index = 0

            st.session_state.selected_models[i] = st.selectbox(
                f"Model {i+1}",
                models_available,
                index=current_selection_index,
                key=f"model_select_{i}"
            )
        with cols[1]:
            if st.button("x", key=f"remove_model_{i}"):
                if st.session_state.model_count > 1:
                    st.session_state.selected_models.pop(i)
                    st.session_state.model_count -= 1
                    st.rerun()

    run = st.button("Run Models", type="primary")

st.title("Running LLMs in parallel")

HISTORY_FILE = "Vertical_chat_history.json"

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("Error decoding chat history file. Starting with empty history.")
            return []
        except Exception as e:
            st.error(f"Could not load chat history: {e}")
            return []
    return []

def save_chat_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        st.error(f"Could not save chat history: {e}")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

if "current_run_results" not in st.session_state:
    st.session_state.current_run_results = None

def handle_delete_response(source_type, entry_index=None, model_response_idx_in_entry=None):
    if source_type == "current":
        if st.session_state.current_run_results and model_response_idx_in_entry is not None:
            if 0 <= model_response_idx_in_entry < len(st.session_state.current_run_results["responses"]):
                st.session_state.current_run_results["responses"].pop(model_response_idx_in_entry)
                if not st.session_state.current_run_results["responses"]:
                    st.session_state.current_run_results = None
    elif source_type == "history":
        if entry_index is not None and model_response_idx_in_entry is not None:
            actual_conversation_index = len(st.session_state.chat_history) - 1 - entry_index
            if (0 <= actual_conversation_index < len(st.session_state.chat_history) and
                0 <= model_response_idx_in_entry < len(st.session_state.chat_history[actual_conversation_index]["responses"])):
                st.session_state.chat_history[actual_conversation_index]["responses"].pop(model_response_idx_in_entry)
                if not st.session_state.chat_history[actual_conversation_index]["responses"]:
                    st.session_state.chat_history.pop(actual_conversation_index)
                save_chat_history(st.session_state.chat_history)

def query_ollama_model(model_name, prompt_text):
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
        cleaned_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        eval_count = response_data.get("eval_count", len(cleaned_content.split())) 
        eval_rate = response_data.get("eval_rate", round(eval_count / duration, 2) if duration > 0 else 0)

        return {
            "model": model_name,
            "duration": duration,
            "eval_count": eval_count,
            "eval_rate": eval_rate,
            "response": cleaned_content
        }
    except Exception as e:
        return {
            "model": model_name,
            "duration": 0,
            "eval_count": 0,
            "eval_rate": 0,
            "response": f"Error: {e}"
        }

def get_truncated_text(text, word_limit=50):
    words = text.split()
    if len(words) > word_limit:
        return ' '.join(words[:50]) + "..."
    return text

def display_interaction(entry, entry_idx=None, is_current_run=False):
    st.markdown(f"**Prompt:** {entry['prompt']}")
    if entry['responses']:
        cols = st.columns(len(entry['responses']))
        for i, res in enumerate(entry['responses']):
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
                full_response_text = res["response"]
                words = full_response_text.split()
                content_is_longer_than_50_words = len(words) > 50
                read_more_toggle_key_prefix = "current" if is_current_run else f"entry_{entry_idx}"
                read_more_toggle_key = f"read_more_{read_more_toggle_key_prefix}_model_{i}"

                if read_more_toggle_key not in st.session_state:
                    st.session_state[read_more_toggle_key] = False

                if content_is_longer_than_50_words and not st.session_state[read_more_toggle_key]:
                    st.write(get_truncated_text(full_response_text, word_limit=50))
                else:
                    st.write(full_response_text)

                with st.container():
                    button_cols = st.columns([0.5, 0.5])
                    with button_cols[0]:
                        if content_is_longer_than_50_words:
                            if not st.session_state[read_more_toggle_key]:
                                if st.button("Read More", key=f"btn_read_{read_more_toggle_key}"):
                                    st.session_state[read_more_toggle_key] = True
                                    st.rerun()
                            else:
                                if st.button("Show Less", key=f"btn_less_{read_more_toggle_key}"):
                                    st.session_state[read_more_toggle_key] = False
                                    st.rerun()
                    with button_cols[1]:
                        delete_button_key = f"delete_response_{read_more_toggle_key_prefix}_{i}"
                        st.button(
                            "Delete This Response",
                            key=delete_button_key,
                            on_click=handle_delete_response,
                            args=("current" if is_current_run else "history", entry_idx if not is_current_run else None, i)
                        )
    st.markdown("---")

if run and prompt.strip():
    if st.session_state.current_run_results:
        st.session_state.chat_history.append(st.session_state.current_run_results)
        save_chat_history(st.session_state.chat_history)
    st.session_state.current_run_results = None

    model_inputs = [model for model in st.session_state.selected_models if model]
    if not model_inputs:
        st.warning("Please select at least one model to generate a response.")
    else:
        cols = st.columns(len(model_inputs))
        model_spinners = {}
        for i, model in enumerate(model_inputs):
            with cols[i]:
                model_color = "blue" if i % 2 == 0 else "red"
                st.markdown(f"<h3 style='color:{model_color};'>{model}</h3>", unsafe_allow_html=True)
                model_spinners[model] = st.empty()
                with model_spinners[model].container():
                    st.spinner(f"Running {model}...")

        raw_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(model_inputs)) as executor:
            future_to_model = {executor.submit(query_ollama_model, model, prompt): model for model in model_inputs}
            for future in concurrent.futures.as_completed(future_to_model):
                result = future.result()
                raw_results.append(result)

        ordered_responses = []
        for model in model_inputs:
            for res in raw_results:
                if res["model"] == model:
                    ordered_responses.append(res)
                    break

        st.session_state.current_run_results = {"prompt": prompt, "responses": ordered_responses}

        for i, res in enumerate(ordered_responses):
            with cols[i]:
                model_spinners[res['model']].empty()
                st.markdown(
                    f"""
                    <div style="background-color:#e6f0ff; padding:10px; border-radius:8px; margin-bottom:10px;">
                        <b>Duration</b>: <span style="color:#3366cc;">{res['duration']} secs</span><br>
                        <b>Eval count</b>: <span style="color:green;">{res['eval_count']} tokens</span><br>
                        <b>Eval rate</b>: <span style="color:green;">{res['eval_rate']} tokens/s</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.write(res["response"])

        st.rerun()

if st.session_state.current_run_results:
    st.subheader("Current Interaction")
    display_interaction(st.session_state.current_run_results, is_current_run=True)
else:
    st.info("Enter a prompt and select models to start a new interaction.")

st.subheader("Previous Interactions")
if st.session_state.chat_history:
    for entry_idx, entry in enumerate(reversed(st.session_state.chat_history)):
        display_interaction(entry, entry_idx=entry_idx, is_current_run=False)
else:
    st.info("No previous interactions found.")
