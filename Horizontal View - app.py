import streamlit as st
import requests
import time
import concurrent.futures
import json
import os
import re
import pyperclip

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

div.stButton button[data-testid*="stButton-primary"] {
    font-size: 14px !important;
    height: 35px !important;
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

HISTORY_FILE = "Horizontal_chat_history.json"

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

def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        st.toast("Copied to clipboard!")
    except Exception as e:
        st.error(f"Could not copy to clipboard: {e}")

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

def regenerate_last_prompt():
    if not st.session_state.chat_history:
        st.warning("No previous prompt to regenerate.")
        return

    last_prompt = st.session_state.chat_history[-1]['prompt']
    selected_models_filtered = [model for model in st.session_state.selected_models if model]

    if not selected_models_filtered:
        st.warning("Please select at least one model.")
        return

    responses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_models_filtered)) as executor:
        future_to_model = {executor.submit(query_ollama_model, model, last_prompt): model for model in selected_models_filtered}

        for future in concurrent.futures.as_completed(future_to_model):
            model_name = future_to_model[future]
            try:
                res = future.result()
                responses.append(res)
            except Exception as exc:
                responses.append({
                    "model": model_name,
                    "duration": 0,
                    "eval_count": 0,
                    "eval_rate": 0,
                    "response": f"Error: {exc}"
                })

    ordered_responses = []
    for model in selected_models_filtered:
        for res in responses:
            if res["model"] == model:
                ordered_responses.append(res)
                break

    st.session_state.chat_history.append({"prompt": last_prompt, "responses": ordered_responses})
    save_chat_history(st.session_state.chat_history)

def delete_model_response(conversation_index, model_response_idx_in_entry):
    actual_conversation_index = len(st.session_state.chat_history) - 1 - conversation_index
    
    if (0 <= actual_conversation_index < len(st.session_state.chat_history) and
        0 <= model_response_idx_in_entry < len(st.session_state.chat_history[actual_conversation_index]["responses"])):
        
        st.session_state.chat_history[actual_conversation_index]["responses"].pop(model_response_idx_in_entry)
        
        if not st.session_state.chat_history[actual_conversation_index]["responses"]:
            st.session_state.chat_history.pop(actual_conversation_index)
            
        save_chat_history(st.session_state.chat_history)

prompt = st.text_area("Prompt", "")

if "model_count" not in st.session_state:
    st.session_state.model_count = 2
if "selected_models" not in st.session_state:
    st.session_state.selected_models = ["", ""]
if "regenerate_clicked" not in st.session_state:
    st.session_state.regenerate_clicked = False

def remove_model(index):
    if st.session_state.model_count > 1:
        st.session_state.model_count -= 1
        st.session_state.selected_models.pop(index)

for i in range(st.session_state.model_count):
    col1, col2 = st.columns([0.97, 0.02])
    with col1:
        if i >= len(st.session_state.selected_models):
            st.session_state.selected_models.append("")
        
        st.session_state.selected_models[i] = st.selectbox(
            f"Model {i+1}",
            models_available,
            index=0 if i >= len(st.session_state.selected_models) or not st.session_state.selected_models[i] else (models_available.index(st.session_state.selected_models[i]) if st.session_state.selected_models[i] in models_available else 0),
            key=f"model_select_{i}"
        )
    with col2:
        st.button("✖", key=f"remove_model_{i}", on_click=remove_model, args=(i,))

selected_models_filtered = [model for model in st.session_state.selected_models if model]

_, col_add, col_regenerate, col_run = st.columns([0.55, 0.15, 0.15, 0.15])
with col_add:
    if st.button("Add New Model"):
        st.session_state.model_count += 1
        st.session_state.selected_models.append("")
        st.rerun()
with col_regenerate:
    if st.button("Regenerate"):
        st.session_state.regenerate_clicked = True
        st.rerun()
with col_run:
    run_clicked = st.button("Run Models", type="primary")

if run_clicked and prompt and selected_models_filtered:
    responses = []
    
    with st.spinner("Generating response..."):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_models_filtered)) as executor:
            future_to_model = {executor.submit(query_ollama_model, model, prompt): model for model in selected_models_filtered}
            
            for future in concurrent.futures.as_completed(future_to_model):
                model_name = future_to_model[future]
                try:
                    res = future.result()
                    responses.append(res)
                except Exception as exc:
                    responses.append({
                        "model": model_name,
                        "duration": 0,
                        "eval_count": 0,
                        "eval_rate": 0,
                        "response": f"Error: {exc}"
                    })

        ordered_responses = []
        for model in selected_models_filtered:
            for res in responses:
                if res["model"] == model:
                    ordered_responses.append(res)
                    break
        
        st.session_state.chat_history.append({"prompt": prompt, "responses": ordered_responses})
        save_chat_history(st.session_state.chat_history)

if st.session_state.regenerate_clicked:
    with st.spinner("Regenerating responses..."):
        regenerate_last_prompt()
    st.session_state.regenerate_clicked = False

st.markdown("---")
st.subheader("Previous Interactions")

def get_truncated_text(text, word_limit=50):
    words = text.split()
    if len(words) > word_limit:
        return ' '.join(words[:word_limit]) + "..."
    return text

if st.session_state.chat_history:
    for entry_idx, entry in enumerate(reversed(st.session_state.chat_history)):
        st.markdown(f"**Prompt:** {entry['prompt']}")
        
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
                
                read_more_toggle_key = f"read_more_entry_{entry_idx}_model_{i}"
                
                if read_more_toggle_key not in st.session_state:
                    st.session_state[read_more_toggle_key] = False
                
                if content_is_longer_than_50_words and not st.session_state[read_more_toggle_key]:
                    st.write(get_truncated_text(full_response_text, word_limit=50))
                else:
                    st.write(full_response_text)
                
                button_cols = st.columns(3)
                
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
                    st.button(
                        "Copy Output",
                        key=f"copy_response_{entry_idx}_{i}",
                        on_click=copy_to_clipboard,
                        args=(full_response_text,)
                    )

                with button_cols[2]:
                    st.button(
                        "Delete This Response",
                        key=f"delete_response_{entry_idx}_{i}",
                        on_click=delete_model_response,
                        args=(entry_idx, i)
                    )
        st.markdown("---")
else:
    st.info("No previous interactions found. Run models to start saving history!")
