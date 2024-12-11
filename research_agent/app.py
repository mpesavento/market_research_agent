import gradio as gr
from datetime import datetime
import markdown
from research_agent.workflow import create_market_research_orchestrator
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction
from research_agent.utils import AgentStatus, PROGRESS_MAP
from typing import Generator
from queue import Queue, Empty
from threading import Thread
import os
from time import time  # Add this import for time tracking



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
    status_text = "⏳ Waiting to start...\n"
    result = None
    start_time = time()  # Track start time

    try:
        # Only start if not already running
        if result is None:
            print("[DEBUG] Starting research process...")
            enhanced_query = enhance_query(query, analysis_depth, focus_areas)

            def status_callback(message: str):
                """
                Callback to update status and progress.
                """
                print(f"[DEBUG] Status callback received: {message}")
                status_queue.put(message)

            print("[DEBUG] Creating orchestrator...")
            orchestrator = create_market_research_orchestrator(
                status_callback=status_callback
            )

            # Run orchestrator in a separate thread
            def run_orchestrator():
                nonlocal result
                print("[DEBUG] Orchestrator thread starting...")
                result = orchestrator.run_research(enhanced_query)
                print("[DEBUG] Orchestrator thread completed")
                status_queue.put(None)  # Signal completion

            thread = Thread(target=run_orchestrator)
            print("[DEBUG] Starting orchestrator thread")
            thread.start()

            # Process status updates
            while True:
                try:
                    status_msg = status_queue.get(timeout=1.0)
                    if status_msg is None:
                        print("[DEBUG] Research complete signal received")
                        break

                    # Append new status to existing status text
                    status_text += f"{status_msg}\n"
                    print(f"[DEBUG] Updated status text (length: {len(status_text)}):\n{status_text}")

                    # Yield all components including current status
                    yield (
                        "",                # intermediate_output
                        "",                # final_report
                        "",                # file_path
                        "",                # error_message
                        status_text,       # status_log
                        ""                 # download_btn
                    )
                except Empty:
                    elapsed = int(time() - start_time)
                    minutes = elapsed // 60
                    seconds = elapsed % 60
                    time_str = f"{minutes}m {seconds}s"
                    print(f"[DEBUG] No status update, elapsed time: {time_str}")
                    continue
                except Exception as e:
                    print(f"[DEBUG] Error in status update loop: {str(e)}")
                    continue

            # After research is complete...
            elapsed = int(time() - start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            status_text += f"\n✅ Research completed in {minutes}m {seconds}s\n"

            # ... rest of the completion code ...

    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        yield (
            "",                # intermediate_output
            "",                # final_report
            "",                # file_path
            error_msg,         # error_message
            status_text + f"\n❌ Error: {error_msg}",  # Append error to status log
            ""                 # download_btn
        )

def create_interface():
    """Create and configure the Gradio interface."""
    custom_css = """
    /* Hide progress bar everywhere by default */
    .progress-container, .progress-bar, .progress-level {
        display: none !important;
    }

    /* Only show progress bar in the agent-status-container */
    #agent-status-container .progress-container,
    #agent-status-container .progress-bar,
    #agent-status-container .progress-level {
        display: block !important;
    }

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
                            "Consumer Behavior"
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


        # Create a dedicated column for the status log
        with gr.Column(elem_id="status-container", scale=1, min_width=400):
            gr.Markdown("🔄 Agent Status", elem_id="status-header")
            status_log = gr.TextArea(
                value="⏳ Waiting to start...",
                label="Status Log",
                lines=10,
                max_lines=15,
                interactive=False,
                autoscroll=True,
                elem_id="status-log"
            )

        # All other components without show_progress
        with gr.Accordion("📋 Intermediate Findings", open=False):
            intermediate_output = gr.Markdown(
                elem_classes="findings-section markdown-content",
                show_label=False,
            )

        with gr.Accordion("🔍 Final Report", open=True):
            final_report = gr.Markdown(
                elem_classes="output-panel markdown-content",
                show_label=False,
            )

        with gr.Row():
            with gr.Column(scale=2):
                file_path = gr.Textbox(
                    label="Report Location",
                    show_label=True,
                    container=True,
                )
            with gr.Column(scale=1):
                download_btn = gr.Button(value="📥 Download Report", visible=True)
                file_output = gr.File(
                    label="Download",
                    interactive=False,
                    visible=True,
                )

        error_message = gr.Markdown(
            elem_classes="error-message",
            show_label=False
        )

        # Update submit button click handler to ensure status_log is included
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
                status_log,
                download_btn
            ],
            show_progress=False
        )

    return interface.queue()

if __name__ == "__main__":
    demo = create_interface()
    environment = os.environ.get("ENV", "DEV")
    if environment == "PROD":
        demo.launch(
            server_name="0.0.0.0",
            server_port=int(os.environ.get("PORT", 7860)),
            share=False,
            quiet=False
        )
    else:
        demo.launch(
            share=True,
            quiet=False
        )
