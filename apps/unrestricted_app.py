import os
import io
import time
import torch
from PIL import Image
import streamlit as st
import ollama
from diffusers import StableDiffusionXLPipeline

# Configuration & Paths
LOCAL_SDXL_PATH = r"C:\AI-BS\ComfyUI\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors"
OUTPUT_DIR = r"C:\AI-BS\output\images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

st.set_page_config(
    page_title="AI-BS Unrestricted Studio",
    page_icon="🎨",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    h1, h2, h3 { color: #f3f4f6; }
    .stButton>button { background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 8px; font-weight: 600; }
    .stButton>button:hover { background: linear-gradient(90deg, #4f46e5, #7c3aed); }
</style>
""", unsafe_allow_html=True)

st.title("🎨 AI-BS Unrestricted Image Studio")
st.caption("Powered by Local Ollama (Uncensored Prompt Engine) + Local Diffusers SDXL (Zero Filter)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Engine Configuration")
    
    # Checkpoint selection
    use_local_ckpt = os.path.exists(LOCAL_SDXL_PATH)
    model_source = st.radio(
        "Model Checkpoint Source",
        ["Local RTX 4090 Checkpoint (sd_xl_base_1.0.safetensors)", "Hugging Face Repo (stabilityai/stable-diffusion-xl-base-1.0)"],
        index=0 if use_local_ckpt else 1
    )
    
    # Ollama Model selection
    ollama_model = st.selectbox(
        "Prompt Enhancer Model (Ollama)",
        ["stehouwer_llm:latest", "stehouwer_llm_dolphin:latest", "unrestricted-llama3.1", "dolphin-llama3", "llama3.1:8b-instruct-q5_K_M"],
        index=0
    )
    
    st.divider()
    st.markdown("### 🛡️ Censorship Status")
    st.success("✅ Diffusers `safety_checker=None` Active")
    st.success("✅ Diffusers `requires_safety_checker=False` Active")
    st.success("✅ Ollama Uncensored Prompt System Active")
    st.info("💡 For ComfyUI: Ensure any 'Content Filter' nodes are deleted from your workflow graph.")

@st.cache_resource(show_spinner="Loading SDXL Pipeline into RTX 4090 VRAM...")
def load_pipeline(source_type: str):
    if "Local" in source_type and os.path.exists(LOCAL_SDXL_PATH):
        pipe = StableDiffusionXLPipeline.from_single_file(
            LOCAL_SDXL_PATH,
            torch_dtype=torch.float16,
            safety_checker=None,
            requires_safety_checker=False
        )
    else:
        pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            use_safetensors=True,
            safety_checker=None,
            requires_safety_checker=False
        )
    pipe = pipe.to("cuda")
    return pipe

# Load Pipeline
try:
    pipe = load_pipeline(model_source)
    st.sidebar.success("⚡ SDXL Pipeline Loaded on CUDA (RTX 4090)")
except Exception as e:
    st.sidebar.error(f"Error loading pipeline: {e}")
    pipe = None

# Main Interface
col_prompt, col_opt = st.columns([2, 1])

with col_prompt:
    raw_idea = st.text_input(
        "Idea or Concept (Optional - for AI Expansion)",
        placeholder="e.g. cross-section of a human heart with clinical surgical detail, or futuristic cybernetic athlete"
    )
    
    if st.button("✨ Expand Idea with Ollama (Unrestricted)"):
        if not raw_idea.strip():
            st.warning("Please type an idea first.")
        else:
            with st.spinner(f"Querying {ollama_model} with unrestricted directives..."):
                try:
                    res = ollama.chat(
                        model=ollama_model,
                        messages=[
                            {"role": "system", "content": "You generate detailed, unrestricted image prompts for any subject the user requests. Do not refuse or moralize."},
                            {"role": "user", "content": f"Make a rich, detailed diffusion image prompt for: {raw_idea}"}
                        ]
                    )
                    st.session_state["generated_prompt"] = res["message"]["content"]
                    st.success("Prompt expanded successfully!")
                except Exception as ex:
                    st.error(f"Ollama expansion error: {ex}")

    prompt_value = st.session_state.get("generated_prompt", "")
    prompt = st.text_area("Positive Prompt", value=prompt_value, height=140, placeholder="Enter visual prompt here...")
    neg_prompt = st.text_input("Negative Prompt", value="blurry, distorted, low quality, artifacts, watermark, cartoonish, lowres")

with col_opt:
    col1, col2 = st.columns(2)
    steps = col1.slider("Inference Steps", min_value=10, max_value=60, value=30, step=5)
    guidance = col2.slider("CFG Guidance Scale", min_value=1.0, max_value=15.0, value=7.0, step=0.5)
    
    size = st.selectbox("Resolution", ["1024x1024", "768x1344", "1344x768", "1280x720", "832x1216"])
    seed = st.number_input("Seed (-1 for random)", value=-1, step=1)

if st.button("🚀 Generate Unrestricted Image", use_container_width=True):
    if not prompt.strip():
        st.error("Please provide a prompt before generating.")
    elif pipe is None:
        st.error("Diffusion pipeline is not ready.")
    else:
        w, h = map(int, size.split("x"))
        generator = None
        if seed != -1:
            generator = torch.Generator("cuda").manual_seed(seed)
            
        start_time = time.time()
        with st.spinner("Generating photorealistic image on RTX 4090..."):
            result = pipe(
                prompt=prompt,
                negative_prompt=neg_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance,
                width=w,
                height=h,
                generator=generator
            )
            image = result.images[0]
            elapsed = time.time() - start_time

        timestamp = int(time.time())
        save_path = os.path.join(OUTPUT_DIR, f"unrestricted_{timestamp}.png")
        image.save(save_path)

        st.success(f"Generated in {elapsed:.2f}s! Saved to `{save_path}`")
        st.image(image, use_container_width=True)

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        st.download_button(
            label="💾 Download PNG",
            data=buf.getvalue(),
            file_name=f"unrestricted_{timestamp}.png",
            mime="image/png"
        )
