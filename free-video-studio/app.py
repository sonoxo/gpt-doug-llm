import os

import gradio as gr

from engine import check_environment, generate_project

DEFAULT_STYLE = (
    "ultra-realistic cinematic photography, natural skin texture, subtle film grain, physically plausible materials, "
    "high dynamic range, restrained color grade, no artificial plastic sheen"
)


def build_app() -> gr.Blocks:
    with gr.Blocks(title="FREE VIDEO STUDIO") as demo:
        gr.Markdown(
            "# 🎬 FREE VIDEO STUDIO\n"
            "**Seedance-style creation workflow with zero paid inference APIs.** "
            "Wan2.2 TI2V-5B handles text/image video; FFmpeg chains shots; optional MMAudio adds synchronized sound."
        )

        with gr.Row():
            env = gr.Textbox(label="Runtime", value=check_environment(), lines=6, interactive=False)
            refresh = gr.Button("Refresh runtime check")
        refresh.click(check_environment, outputs=env)

        mode = gr.Radio(["Text → Video", "Image → Video", "Storyboard"], value="Text → Video", label="Mode")
        reference = gr.Image(type="filepath", label="Reference image / continuity anchor (optional except Image → Video)")

        with gr.Row():
            scene = gr.Textbox(
                label="Scene + subject",
                placeholder="A woman in a charcoal coat waits alone under rain-soaked neon signs in downtown Richmond...",
                lines=3,
            )
            action = gr.Textbox(
                label="Action",
                placeholder="She looks over her shoulder, exhales, then walks toward camera as traffic passes behind her...",
                lines=3,
            )

        storyboard = gr.Textbox(
            label="Storyboard — one shot per line (Storyboard mode)",
            placeholder=(
                "SHOT 1: Wide establishing shot; subject exits a black sedan into light rain.\n"
                "SHOT 2: Medium tracking shot; subject crosses the sidewalk and glances toward camera.\n"
                "SHOT 3: Tight close-up; raindrops on face, subtle breath, neon reflections in eyes."
            ),
            lines=6,
        )

        with gr.Accordion("Director controls", open=True):
            camera = gr.Textbox(
                label="Camera + lens + movement",
                value="35mm cinema lens, slow stabilized dolly-in, realistic handheld micro-movement, natural motion blur",
            )
            lighting = gr.Textbox(
                label="Lighting",
                value="motivated practical lighting, soft contrast, realistic reflections, volumetric atmosphere",
            )
            style = gr.Textbox(label="Look", value=DEFAULT_STYLE, lines=2)
            continuity = gr.Textbox(
                label="Continuity lock",
                placeholder="Same face, hairstyle, charcoal coat, silver chain, rainy night location and neon palette in every shot.",
                lines=2,
            )

        with gr.Row():
            orientation = gr.Radio(["Landscape 1280×704", "Portrait 704×1280"], value="Landscape 1280×704", label="Frame")
            seconds = gr.Slider(2, 8, value=5, step=1, label="Seconds per shot")
            seed = gr.Number(value=42, precision=0, label="Seed (-1 = random)")

        chain = gr.Checkbox(value=True, label="Chain storyboard shots using the previous shot's final frame")
        add_audio = gr.Checkbox(value=False, label="Add synchronized audio with optional free MMAudio (Linux backend)")
        audio_prompt = gr.Textbox(
            label="Audio direction",
            placeholder="Rain on pavement, distant traffic, jacket movement, footsteps, low city ambience; no music.",
        )

        generate = gr.Button("GENERATE VIDEO", variant="primary")
        output_video = gr.Video(label="Final export")
        logs = gr.Textbox(label="Generation log / provenance", lines=18)

        generate.click(
            fn=generate_project,
            inputs=[
                mode,
                scene,
                action,
                storyboard,
                reference,
                camera,
                lighting,
                style,
                continuity,
                orientation,
                seconds,
                seed,
                chain,
                add_audio,
                audio_prompt,
            ],
            outputs=[output_video, logs],
        )

        gr.Markdown(
            "### $0 software path\n"
            "No Seedance subscription, no paid LLM, and no paid generation API is required. "
            "The video model is downloaded locally. Apple Silicon automatically uses MLX-Gen; Linux/NVIDIA uses the official Wan2.2 CUDA path. Video diffusion is still compute- and memory-intensive."
        )
    return demo


if __name__ == "__main__":
    build_app().queue(default_concurrency_limit=1).launch(
        server_name=os.getenv("STUDIO_HOST", "127.0.0.1"),
        server_port=int(os.getenv("STUDIO_PORT", "7860")),
        share=False,
        show_error=True,
    )
