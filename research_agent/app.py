import os
from datetime import datetime
from time import time
import markdown
import gradio as gr
from typing import Generator
from queue import Queue, Empty
from threading import Thread
from research_agent.workflow import create_market_research_orchestrator
from research_agent.utils import create_pdf_from_markdown
from research_agent.prompts import DEPTH_PROMPTS, FOCUS_PROMPTS


def enhance_query(query: str, depth: str, focus_areas: list) -> str:
    """Enhance the research query with depth and focus specifications."""
    selected_focus_prompts = [FOCUS_PROMPTS[area] for area in focus_areas if area in FOCUS_PROMPTS]

    print(f"[DEBUG] Enhancing query for focus areas: {focus_areas}")

    enhanced_query = f"""Conduct a {depth.lower()} market analysis regarding: {query}

Analysis Depth: {depth}
{DEPTH_PROMPTS[depth]}

Selected Focus Areas:
{chr(10).join(selected_focus_prompts)}

Please structure the analysis to address ONLY the selected focus areas systematically."""

    return enhanced_query

def convert_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML with basic styling."""
    html = markdown.markdown(markdown_text)
    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto;">
        {html}
    </div>
    """

def format_intermediate_findings(findings_dict: dict) -> str:
    """Format intermediate findings dictionary into markdown string."""
    if not findings_dict:
        return ""

    content = "# Market Research - Intermediate Findings\n\n"
    content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for agent, data in findings_dict.items():
        if isinstance(data, dict) and "findings" in data:
            content += f"## {agent.replace('_', ' ').title()}\n"
            content += f"{data['findings']}\n\n"
    return content

def save_findings(findings_dict: dict, timestamp: str = None, format: str = "markdown") -> tuple[str, str, str]:
    """
    Save intermediate findings in the specified format.
    """
    if not findings_dict:
        return "", "", ""

    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        reports_dir = os.path.abspath(os.path.join(os.getcwd(), "reports"))
        os.makedirs(reports_dir, exist_ok=True)

        # Use the common formatting function
        findings_content = format_intermediate_findings(findings_dict)

        if format == "markdown":
            file_path = os.path.join(reports_dir, f"findings_{timestamp}.md")
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(findings_content)
            return file_path, findings_content, ""

        elif format == "html":
            file_path = os.path.join(reports_dir, f"findings_{timestamp}.html")
            html_content = convert_to_html(findings_content)
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(html_content)
            return file_path, html_content, ""

        elif format == "pdf":
            try:
                pdf_path = os.path.join(reports_dir, f"findings_{timestamp}.pdf")
                print(f"[DEBUG] Creating PDF at: {pdf_path}")

                success = create_pdf_from_markdown(
                    markdown_content=findings_content,
                    output_file=pdf_path,
                    title="Market Research - Intermediate Findings"
                )

                if success and os.path.exists(pdf_path):
                    print(f"[DEBUG] PDF created successfully at: {pdf_path}")
                    return pdf_path, findings_content, ""
                else:
                    return "", findings_content, f"Error: PDF file was not created at {pdf_path}"

            except Exception as pdf_error:
                print(f"[DEBUG] PDF creation error: {str(pdf_error)}")
                return "", findings_content, f"Error creating PDF: {str(pdf_error)}"

        else:
            return "", findings_content, f"Unsupported format: {format}"

    except Exception as e:
        print(f"[DEBUG] Error saving findings: {str(e)}")
        return "", findings_content, f"Error saving findings: {str(e)}"

def save_report(content: str, timestamp: str = None, format: str = "markdown") -> tuple[str, str, str]:
    """
    Save the final report in the specified format.
    """
    if not content:
        return "", "", ""

    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Get absolute path for reports directory
        reports_dir = os.path.abspath(os.path.join(os.getcwd(), "reports"))
        os.makedirs(reports_dir, exist_ok=True)

        report_content = "# Market Research Report\n\n"
        report_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report_content += content

        if format == "markdown":
            file_path = os.path.join(reports_dir, f"report_{timestamp}.md")
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(report_content)
            return file_path, report_content, ""

        elif format == "html":
            file_path = os.path.join(reports_dir, f"report_{timestamp}.html")
            html_content = convert_to_html(report_content)
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(html_content)
            return file_path, html_content, ""

        elif format == "pdf":
            try:
                # Create paths
                pdf_path = os.path.join(reports_dir, f"report_{timestamp}.pdf")

                print(f"[DEBUG] Creating PDF at: {pdf_path}")

                # Convert to PDF using our utility function
                success = create_pdf_from_markdown(
                    markdown_content=report_content,
                    output_file=pdf_path,
                    title="Market Research Report"
                )

                if success and os.path.exists(pdf_path):
                    print(f"[DEBUG] PDF created successfully at: {pdf_path}")
                    return pdf_path, report_content, ""
                else:
                    return "", report_content, f"Error: PDF file was not created at {pdf_path}"

            except Exception as pdf_error:
                print(f"[DEBUG] PDF creation error: {str(pdf_error)}")
                return "", report_content, f"Error creating PDF: {str(pdf_error)}"

        else:
            return "", report_content, f"Unsupported format: {format}"

    except Exception as e:
        print(f"[DEBUG] General error in save_report: {str(e)}")
        return "", report_content, f"Error saving report: {str(e)}"

def conduct_research(
    query: str,
    analysis_depth: str,
    focus_areas: list,
) -> Generator[tuple, None, None]:
    """Generator function to conduct market research and yield updates."""
    status_queue = Queue()
    status_text = ""  # Accumulated status for UI
    result = None
    start_time = time()
    last_status_time = start_time  # Track time of last status update
    last_debug_time = start_time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_occurred = False  # Add flag to track errors

    try:
        if result is None:
            print("[DEBUG] Initializing research orchestrator...")
            enhanced_query = enhance_query(query, analysis_depth, focus_areas)

            def status_callback(message: str):
                """Callback to update status and progress."""
                nonlocal last_status_time  # Add access to last_status_time
                last_status_time = time()  # Update time when status received
                print(f"[STATUS] {message}")
                status_queue.put(message)

            print("[DEBUG] Creating orchestrator...")
            orchestrator = create_market_research_orchestrator(
                status_callback=status_callback
            )

            def run_orchestrator():
                nonlocal result, error_occurred
                try:
                    print("[DEBUG] Starting research execution...")
                    result = orchestrator.run_research(
                        enhanced_query,
                        focus_areas=focus_areas
                    )
                    print("[DEBUG] Research execution completed")
                except Exception as e:
                    error_occurred = True
                    status_queue.put(f"ERROR: {str(e)}")
                finally:
                    status_queue.put(None)  # Signal completion

            thread = Thread(target=run_orchestrator)
            thread.start()

            # Process status updates
            while True:
                try:
                    status_msg = status_queue.get(timeout=1.0)
                    if status_msg is None:
                        print("[DEBUG] Research complete signal received")
                        break

                    # Check if the message indicates an error
                    if status_msg.startswith("ERROR:"):
                        error_occurred = True
                        status_text += f"❌ {status_msg}\n"
                        yield (
                            "",                # intermediate_output
                            "",                # final_report
                            None,              # report_file_md
                            None,              # report_file_html
                            None,              # report_file_pdf
                            None,              # findings_file_md
                            None,              # findings_file_html
                            None,              # findings_file_pdf
                            status_msg,        # error_message
                            status_text,       # status_log
                        )
                        break  # Exit the loop on error

                    # Update UI status text with new message
                    if not status_text:
                        status_text = "⏳ Research Started\n"
                    status_text += f"{status_msg}\n"

                    # Format intermediate findings as string
                    current_findings = format_intermediate_findings(
                        result.get("agent_outputs", {}) if result else {}
                    )

                    yield (
                        current_findings,     # intermediate_output
                        "",                   # final_report
                        None,                # report_file_md
                        None,                # report_file_html
                        None,                # report_file_pdf
                        None,                # findings_file_md
                        None,                # findings_file_html
                        None,                # findings_file_pdf
                        "",                  # error_message
                        status_text,       # status_log
                    )

                except Empty:
                    if error_occurred:  # Exit the loop if an error occurred
                        break
                    current_time = time()
                    time_since_status = int(current_time - last_status_time)

                    if int(current_time - last_debug_time) >= 10:
                        minutes = time_since_status // 60
                        seconds = time_since_status % 60
                        print(f"[DEBUG] Time since last status: {minutes}m {seconds}s")
                        last_debug_time = current_time
                    continue

        # After research is complete...
        if result and not error_occurred:
            try:
                # Generate findings content first
                final_report_content = result.get("final_report", "")

                # Generate reports in all formats
                report_path_md, _, report_error_md = save_report(
                    content=final_report_content,
                    timestamp=timestamp,
                    format="markdown"
                )
                report_path_html, _, report_error_html = save_report(
                    content=final_report_content,
                    timestamp=timestamp,
                    format="html"
                )
                report_path_pdf, _, report_error_pdf = save_report(
                    content=final_report_content,
                    timestamp=timestamp,
                    format="pdf"
                )

                # Save findings in all formats
                findings_path_md, _, findings_error_md = save_findings(
                    findings_dict=result.get("agent_outputs", {}),
                    timestamp=timestamp,
                    format="markdown"
                )
                findings_path_html, _, findings_error_html = save_findings(
                    findings_dict=result.get("agent_outputs", {}),
                    timestamp=timestamp,
                    format="html"
                )
                findings_path_pdf, _, findings_error_pdf = save_findings(
                    findings_dict=result.get("agent_outputs", {}),
                    timestamp=timestamp,
                    format="pdf"
                )

                # Collect all errors
                error_msg = " ".join(filter(None, [
                    report_error_md, report_error_html, report_error_pdf,
                    findings_error_md, findings_error_html, findings_error_pdf
                ]))

                # Format final findings as string
                final_findings = format_intermediate_findings(result.get("agent_outputs", {}))

                # Ensure report_path is None if it's not a valid file
                if report_path_md and not os.path.isfile(report_path_md):
                    report_path_md = None
                    error_msg = f"Error: Generated report path is invalid: {report_path_md}"

                # Ensure findings_path is None if it's not a valid file
                if findings_path_md and not os.path.isfile(findings_path_md):
                    findings_path_md = None
                    error_msg = f"{error_msg}\nError: Generated findings path is invalid: {findings_path_md}"

                yield (
                    final_findings,                  # intermediate_output
                    final_report_content,           # final_report
                    report_path_md,                  # report_file_md
                    report_path_html,                # report_file_html
                    report_path_pdf,                 # report_file_pdf
                    findings_path_md,                # findings_file_md
                    findings_path_html,              # findings_file_html
                    findings_path_pdf,               # findings_file_pdf
                    error_msg,                       # error_message
                    status_text + "\n✅ Files saved successfully!" if not error_msg else status_text + f"\n⚠️ {error_msg}",  # status_log
                )

            except Exception as e:
                error_msg = f"Error processing results: {str(e)}"
                yield (
                    "",                # intermediate_output
                    "",                # final_report
                    None,              # report_file_md
                    None,              # report_file_html
                    None,              # report_file_pdf
                    None,              # findings_file_md
                    None,              # findings_file_html
                    None,              # findings_file_pdf
                    error_msg,         # error_message
                    status_text + f"\n❌ Error: {error_msg}",  # status_log
                )

    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        yield (
            "",                # intermediate_output
            "",                # final_report
            None,             # report_file_md
            None,             # report_file_html
            None,             # report_file_pdf
            None,             # findings_file_md
            None,             # findings_file_html
            None,             # findings_file_pdf
            error_msg,         # error_message
            status_text + f"\n❌ Error: {error_msg}",  # status_log
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
            with gr.Column(scale=1):
                report_file_md = gr.File(
                    label="Download Report (Markdown)",
                    visible=True,
                    height=40,
                    interactive=False
                )
                report_file_html = gr.File(
                    label="Download Report (HTML)",
                    visible=True,
                    height=40,
                    interactive=False
                )
                report_file_pdf = gr.File(
                    label="Download Report (PDF)",
                    visible=True,
                    height=40,
                    interactive=False
                )

            with gr.Column(scale=1):
                findings_file_md = gr.File(
                    label="Download Findings (Markdown)",
                    visible=True,
                    height=40,
                    interactive=False
                )
                findings_file_html = gr.File(
                    label="Download Findings (HTML)",
                    visible=True,
                    height=40,
                    interactive=False
                )
                findings_file_pdf = gr.File(
                    label="Download Findings (PDF)",
                    visible=True,
                    height=40,
                    interactive=False
                )

        error_message = gr.Markdown(
            elem_classes="error-message",
            show_label=False
        )

        # Update submit button click handler with new outputs
        submit_btn.click(
            fn=conduct_research,
            inputs=[
                query,
                analysis_depth,
                focus_areas,
            ],
            outputs=[
                intermediate_output,
                final_report,
                report_file_md,
                report_file_html,
                report_file_pdf,
                findings_file_md,
                findings_file_html,
                findings_file_pdf,
                error_message,
                status_log,
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
