import gradio as gr
import pandas as pd

# Hugging Face'e yukledigin sentetik veri setinin dogrudan linki
DATASET_URL = "https://huggingface.co/datasets/ozgezelal/irrigation-desicion-engine-microservice/resolve/main/irrigation_microservice_dataset.json"

try:
    df = pd.read_json(DATASET_URL)
except Exception as e:
    df = None

def simulate_microservice_pipeline():
    if df is None or df.empty:
        return "Dataset could not be loaded.", "Error", "Error"
    
    # Veri setinden rastgele bir satir secerek mikroservis akisini simule ediyoruz
    random_row = df.sample(n=1).iloc[0]
    inputs = random_row['inputs']
    engine = random_row['deterministic_engine_outputs']
    ai_text = random_row['ai_explanation_layer']['generated_text']
    
    input_text = (
        f"🌾 Soil Moisture: {inputs['soil_moisture']}%\n"
        f"🌡️ Temperature: {inputs['temperature']}°C\n"
        f"💧 Humidity: {inputs['humidity']}%\n"
        f"🌧️ Rainfall: {inputs['rainfall']} mm\n"
        f"☀️ Evapotranspiration (ET₀): {inputs['evapotranspiration_et0']}"
    )
    
    engine_text = (
        f"📊 Water Stress Index: {engine['water_stress_index']}\n"
        f"🚨 Irrigation Recommended: {engine['irrigation_recommended']}\n"
        f"🚰 Water Needed: {engine['water_needed_mm']} mm"
    )
    
    return input_text, engine_text, ai_text

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🌊 Intelligent Irrigation Decision Engine — Microservice Data Pipeline Demo")
    gr.Markdown("This demo simulates the data flow across microservices. Click the button to fetch telemetry data, see the deterministic math engine output, and the final OpenRouter AI explanation layer.")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 📡 Microservice 1: Weather & Sensor Inputs")
            input_box = gr.Textbox(label="Raw Telemetry Data", lines=6)
        with gr.Column():
            gr.Markdown("### ⚙️ Microservice 2: Deterministic Decision Engine")
            engine_box = gr.Textbox(label="Rule-Based Aggregation Outputs", lines=6)
            
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🤖 Microservice 3: AI Explanation Layer (OpenRouter)")
            ai_box = gr.Textbox(label="LLM Human-Readable Summary", lines=3)
            
    trigger_btn = gr.Button("🚀 Trigger Next Microservice Pipeline Event", variant="primary")
    trigger_btn.click(fn=simulate_microservice_pipeline, inputs=[], outputs=[input_box, engine_box, ai_box])

demo.launch()
