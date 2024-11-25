import gradio as gr
from datetime import datetime
import markdown
from research_agent.workflow import create_market_research_orchestrator
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction
from research_agent.utils import AgentStatus, PROGRESS_MAP
from typing import Generator
from queue import Queue
from threading import Thread
import os

# class GradioCallbackHandler(BaseCallbackHandler):
#     def __init__(self, gradio_progress_callback=None):
#         self.gradio_progress_callback = gradio_progress_callback

#     def on_agent_action(self, action, color="blue", **kwargs):
#         if self.gradio_progress_callback:
#             # Format the action message
#             if isinstance(action, AgentAction):
#                 message = f"🤖 Tool: {action.tool}\nInput: {action.tool_input}"
#             else:
#                 message = f"🤖 {action}"
#             print(f"Gradio callback: {message}")
#             self.gradio_progress_callback(message)

#     def on_tool_start(self, tool_name, tool_input, **kwargs):
#         if self.gradio_progress_callback:
#             self.gradio_progress_callback(f"🔧 Starting tool: {tool_name}")

#     def on_tool_end(self, output, **kwargs):
#         if self.gradio_progress_callback:
#             self.gradio_progress_callback(f"✅ Tool finished. Output: {output}")

def enhance_query(query: str, depth: str, focus_areas: list) -> str:
    """Enhance the research query with depth and focus specifications."""
    depth_prompts = {
        "Basic": "Provide a high-level overview focusing on key points",
        "Detailed": "Conduct a thorough analysis with specific examples and data",
        "Comprehensive": "Perform an exhaustive analysis with detailed insights, trends, and recommendations"
    }

    focus_prompts = {
        "Market Trends": "- Analyze current and emerging market trends\n- Identify growth patterns and market size\n- Highlight industry innovations",
        "Competitor Analysis": "- Evaluate major competitors and their market share\n- Compare product features and pricing\n- Assess competitive advantages",
        "Consumer Behavior": "- Examine target demographics and preferences\n- Analyze purchasing patterns\n- Identify key decision factors",
        "Technology Features": "- Review current technology capabilities\n- Assess emerging technologies\n- Compare technical specifications",
        "Pricing Strategy": "- Analyze current market pricing\n- Evaluate price-performance ratios\n- Identify pricing trends and strategies"
    }

    selected_focus_prompts = [focus_prompts[area] for area in focus_areas if area in focus_prompts]

    enhanced_query = f"""Conduct a {depth.lower()} market analysis regarding: {query}

Analysis Depth: {depth}
{depth_prompts[depth]}

Focus Areas:
{chr(10).join(selected_focus_prompts)}

Please structure the analysis to address each focus area systematically."""

    return enhanced_query

def convert_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML with basic styling."""
    html = markdown.markdown(markdown_text)
    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto;">
        {html}
    </div>
    """

def save_report(content: str, format: str = "markdown") -> tuple[str, str, str]:
    """
    Save the report in the specified format.

    Returns:
        tuple[str, str, str]: (file_path, preview_content, error_message)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        if format == "markdown":
            file_path = f"reports/report_{timestamp}.md"
            with open(file_path, "w") as f:
                f.write(content)
            return file_path, content, ""

        elif format == "html":
            file_path = f"reports/report_{timestamp}.html"
            html_content = convert_to_html(content)
            with open(file_path, "w") as f:
                f.write(html_content)
            return file_path, html_content, ""

        elif format == "pdf":
            # PDF conversion would go here
            return "", content, "PDF export not yet implemented"

    except Exception as e:
        return "", content, f"Error saving report: {str(e)}"

def conduct_research(
    query: str,
    analysis_depth: str,
    focus_areas: list,
    export_format: str = "markdown"
) -> Generator[tuple, None, None]:
    """
    Generator function to conduct market research and yield updates.
    """
    status_queue = Queue()

    try:
        enhanced_query = enhance_query(query, analysis_depth, focus_areas)

        def status_callback(message: str):
            """
            Callback to update status and progress.
            """
            progress_value = PROGRESS_MAP.get(message, 0)
            status_queue.put((message, progress_value))

        # Create orchestrator with our status callback
        orchestrator = create_market_research_orchestrator(
            status_callback=status_callback
        )

        # Initial status
        yield (
            "",                # intermediate_output
            "",                # final_report
            "",                # file_path
            "",                # error_message
            AgentStatus.WAITING,  # status_display
            0,                # progress_bar
            ""             # download_btn
        )

        # Run orchestrator in a separate thread
        def run_orchestrator():
            nonlocal result
            result = orchestrator.run_research(enhanced_query)
            status_queue.put(None)  # Signal completion

        result = None
        thread = Thread(target=run_orchestrator)
        thread.start()

        # Process status updates as they come in
        while True:
            status_update = status_queue.get()
            if status_update is None:  # Research complete
                break

            status_msg, progress_value = status_update
            # Update the UI with the new status and progress
            yield (
                "",                # intermediate_output
                "",                # final_report
                "",                # file_path
                "",                # error_message
                status_msg,        # status_display
                progress_value,    # progress_bar
                ""             # download_btn
            )

        # Format intermediate findings
        intermediate_findings = ""
        for agent_name, output in result.get("agent_outputs", {}).items():
            if "findings" in output:
                intermediate_findings += f"\n### {agent_name.replace('_', ' ').title()}\n"
                intermediate_findings += output["findings"]
                intermediate_findings += "\n---\n"

        # Yield intermediate findings
        yield (
            intermediate_findings,  # intermediate_output
            "",                    # final_report
            "",                    # file_path
            "",                    # error_message
            "Processing findings...", # status_display
            0.9,                   # progress_bar (90% complete)
            ""                  # download_btn
        )

        # Convert and save in requested format
        file_path, preview_content, error = save_report(
            result["final_report"],
            export_format
        )

        if error:
            yield (
                intermediate_findings,          # intermediate_output
                result.get("final_report", ""), # final_report
                "",                            # file_path
                error,                         # error_message
                f"⚠️ Error: {error}",          # status_display
                0,                             # progress_bar (reset on error)
                ""                          # download_btn
            )
        else:
            yield (
                intermediate_findings,          # intermediate_output
                result.get("final_report", ""), # final_report
                file_path,                     # file_path
                "",                            # error_message
                "✅ Research workflow complete!", # status_display
                1.0,                           # progress_bar (100% complete)
                "📥 Download Report"                           # download_btn
            )

    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        yield (
            "",                # intermediate_output
            "",                # final_report
            "",                # file_path
            error_msg,         # error_message
            AgentStatus.WAITING, # status_display
            0,                # progress_bar (reset on error)
            ""             # download_btn
        )

def create_interface():
    """Create and configure the Gradio interface."""
    custom_css = """
    /* General container styling */
    .container {
        max-width: 1000px;
        margin: auto;
    }

    /* Output panel styling */
    .output-panel {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        background-color: #f9f9f9;
        color: #2c3e50;  /* Dark blue-grey text */
    }

    /* Findings section styling */
    .findings-section {
        margin: 20px 0;
        padding: 15px;
        border-left: 4px solid #2c3e50;
        background-color: #f8f9fa;
        color: #2c3e50;
    }

    /* Error message styling */
    .error-message {
        color: #dc3545;
        font-weight: 500;
    }

    /* Ensure text is readable in all states */
    .markdown-text {
        color: #2c3e50 !important;
    }

    /* Style markdown content */
    .markdown-content h1,
    .markdown-content h2,
    .markdown-content h3 {
        color: #2c3e50;
        margin-top: 1em;
        margin-bottom: 0.5em;
    }

    .markdown-content p {
        color: #2c3e50;
        line-height: 1.6;
    }

    /* Ensure contrast in dark mode */
    @media (prefers-color-scheme: dark) {
        .output-panel,
        .findings-section {
            background-color: #2c3e50;
            color: #f8f9fa;
        }

        .markdown-text,
        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content p {
            color: #f8f9fa !important;
        }
    }
    """

    with gr.Blocks(
        title="Market Research Assistant",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
            neutral_hue="slate",
            text_size=gr.themes.sizes.text_md,
        ),
        css=custom_css
    ) as interface:
        gr.Markdown("""
        # 📊 Market Research Assistant
        Generate comprehensive market analysis reports with customizable focus areas and depth.
        """, elem_classes="markdown-text")

        with gr.Row():
            with gr.Column(scale=2):
                query = gr.Textbox(
                    label="Research Query",
                    placeholder="Enter your market research query here...",
                    lines=3
                )

                with gr.Row():
                    analysis_depth = gr.Radio(
                        choices=["Basic", "Detailed", "Comprehensive"],
                        value="Detailed",
                        label="Analysis Depth"
                    )
                    focus_areas = gr.CheckboxGroup(
                        choices=[
                            "Market Trends",
                            "Competitor Analysis",
                            "Consumer Behavior",
                            "Technology Features",
                            "Pricing Strategy"
                        ],
                        value=["Market Trends", "Competitor Analysis", "Consumer Behavior"],
                        label="Focus Areas"
                    )
                    export_format = gr.Radio(
                        choices=["markdown", "html", "pdf"],
                        value="markdown",
                        label="Export Format"
                    )

                submit_btn = gr.Button("🔍 Generate Report", variant="primary", size="lg")

        with gr.Row():
            with gr.Column():
                gr.Markdown("🔄 Agent Status")
                status_display = gr.Markdown(
                    elem_classes="status-display",
                    show_label=False,
                    value=AgentStatus.WAITING
                )
                progress_bar = gr.Slider(
                    minimum=0,
                    maximum=1.0,
                    value=0,
                    label="Progress",
                    interactive=False,
                    elem_id="research-progress"
                )


        # Wrap intermediate findings in Accordion
        with gr.Accordion("📋 Intermediate Findings", open=False):
            with gr.Column(show_progress=False):
                intermediate_output = gr.Markdown(
                    elem_classes="findings-section markdown-content",
                    show_label=False,
                )

        with gr.Accordion("🔍 Final Report", open=True):
            with gr.Column(show_progress=False):
                final_report = gr.Markdown(
                    elem_classes="output-panel markdown-content",
                    show_label=False,
                )

        with gr.Row():
            with gr.Column(scale=2, show_progress=False):
                file_path = gr.Textbox(
                    label="Report Location",
                    show_label=True,
                    container=True,
                )
            # Add download button
            with gr.Column(scale=1):
                download_btn = gr.Button(value="📥 Download Report", visible=True)

                # Create the download component
                file_output = gr.File(
                    label="Download",
                    interactive=False,
                    visible=True,
                )

        def prepare_download(filepath: str) -> str:
            """Prepare file for download if it exists."""
            if filepath and filepath.strip() and os.path.exists(filepath):
                return filepath
            return None

        # Update download button click handler
        download_btn.click(
            fn=prepare_download,
            inputs=[file_path],
            outputs=[file_output],
            api_name="download_report"
        )

        error_message = gr.Markdown(
            elem_classes="error-message",
            show_label=False
        )

        # Update submit button click handler
        submit_btn.click(
            fn=conduct_research,
            inputs=[
                query,
                analysis_depth,
                focus_areas,
                export_format
            ],
            outputs=[
                intermediate_output,
                final_report,
                file_path,
                error_message,
                status_display,
                progress_bar,
                download_btn
            ]
        )
        # .then(  # Chain the enable_download function
        #     fn=enable_download,
        #     inputs=[file_path],
        #     outputs=[download_btn]
        # )

    return interface.queue()

if __name__ == "__main__":
    demo = create_interface()
    environment = os.environ.get("ENV", "DEV")
    if environment == "PROD":
        demo.launch(
            server_name="0.0.0.0",
            server_port=int(os.environ.get("PORT", 7860)),
            share=False
        )
    else:
        demo.launch(share=True)
