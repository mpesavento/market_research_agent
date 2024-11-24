# app.py
import gradio as gr
from langchain_core.messages import HumanMessage
from utils import AgentType
from workflow import MarketResearchWorkflow
import time
import markdown
from datetime import datetime
import pdfkit
from pathlib import Path
import os
import json
from typing import Optional

def convert_to_html(markdown_text: str, include_style: bool = True) -> str:
    """Convert markdown to HTML with optional styling"""
    html_content = markdown.markdown(markdown_text)
    if include_style:
        return f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 800px;
                        margin: 40px auto;
                        padding: 20px;
                        line-height: 1.6;
                    }}
                    h1, h2, h3 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                    }}
                    hr {{
                        border: none;
                        border-top: 2px solid #eee;
                        margin: 2em 0;
                    }}
                    .findings-section {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }}
                    .timestamp {{
                        color: #666;
                        font-style: italic;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
        </html>
        """
    return html_content

def save_report(markdown_text: str, format: str = "markdown") -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Save report in specified format and return paths.
    Returns: (file_path, preview_content, error_message)
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        if format == "markdown":
            filepath = reports_dir / f"report_{timestamp}.md"
            filepath.write_text(markdown_text)
            return str(filepath), markdown_text, None

        elif format == "html":
            filepath = reports_dir / f"report_{timestamp}.html"
            html_content = convert_to_html(markdown_text)
            filepath.write_text(html_content)
            return str(filepath), html_content, None

        elif format == "pdf":
            filepath = reports_dir / f"report_{timestamp}.pdf"
            html_content = convert_to_html(markdown_text)
            try:
                pdfkit.from_string(html_content, str(filepath))
                return str(filepath), "PDF preview not available in interface", None
            except Exception as e:
                return None, None, f"PDF generation failed: {str(e)}"

        return None, None, f"Unsupported format: {format}"

    except Exception as e:
        return None, None, f"Error saving report: {str(e)}"

def conduct_research(
    query: str,
    analysis_depth: str,
    focus_areas: list,
    export_format: str = "markdown",
    progress=gr.Progress()
) -> tuple[str, str, str, str, str]:
    """
    Conduct market research and return results with progress updates.

    Args:
        query (str): The primary research question or topic to analyze. Should be a clear,
            specific request for market research (e.g., "Analyze the electric vehicle market in Europe").

        analysis_depth (str): Level of detail for the analysis. Must be one of:
            - "Basic": High-level overview
            - "Detailed": Standard depth analysis
            - "Comprehensive": In-depth analysis with extensive details

        focus_areas (list): List of specific aspects to analyze. Valid options include:
            - "Market Trends"
            - "Competitor Analysis"
            - "Consumer Behavior"
            - "Technology Features"
            - "Pricing Strategy"

        export_format (str, optional): Format for the saved report. Defaults to "markdown".
            Must be one of:
            - "markdown": .md file with plain text formatting
            - "html": Styled HTML document
            - "pdf": PDF document with formatting

        progress (gr.Progress, optional): Gradio progress bar instance for updating UI.
            Automatically provided by Gradio.

    Returns:
        tuple[str, str, str, str, str]: A tuple containing:
            - intermediate_findings: Markdown formatted string of findings from each agent
            - final_report: Synthesized final report text
            - file_path: Path to the saved report file
            - preview_content: HTML preview of the report (if format is html)
            - error_message: Error description if any occurred, empty string otherwise

    Raises:
        Exception: If there's an error during research or report generation

    Example:
        >>> findings, report, path, preview, error = conduct_research(
        ...     query="Analyze the electric vehicle market in Europe",
        ...     analysis_depth="Detailed",
        ...     focus_areas=["Market Trends", "Competitor Analysis"],
        ...     export_format="pdf"
        ... )
    """
    workflow = MarketResearchWorkflow()

    enhanced_query = f"""{query}
    Please provide a {analysis_depth} analysis focusing on: {', '.join(focus_areas)}.
    """

    initial_state = {
        "messages": [HumanMessage(content=enhanced_query)],
        "next_agent": "market_trends",
        "research_data": {},
        "final_report": None
    }

    intermediate_findings = []
    final_report_text = ""
    error_msg = None

    try:
        for i, output in enumerate(workflow.run(initial_state)):
            agent_name = output["next_agent"].replace("_", " ").title()
            progress((i + 1)/4)

            # Store intermediate findings
            if "research_data" in output:
                for agent, data in output["research_data"].items():
                    if "findings" in data:
                        intermediate_findings.append(f"### {agent.replace('_', ' ').title()}\n\n{data['findings']}\n\n---\n")

            if output.get("final_report"):
                final_report_text = output["final_report"]
                progress(1.0)
                break

        # Combine all text into markdown
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_report = f"""# Market Research Analysis Report

*Generated on: {timestamp}*

## Analysis Parameters
- **Depth**: {analysis_depth}
- **Focus Areas**: {', '.join(focus_areas)}

## Intermediate Findings

{''.join(intermediate_findings)}

## Final Report

{final_report_text}
"""

        # Save report in requested format
        file_path, preview_content, save_error = save_report(full_report, export_format)
        if save_error:
            error_msg = save_error

        return (
            "\n".join(intermediate_findings),
            final_report_text,
            file_path or "",
            preview_content or "",
            error_msg or ""
        )

    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        return "", "", "", "", error_msg

def create_interface():
    """Create and configure the Gradio interface."""

    custom_css = """
    .container { max-width: 1000px; margin: auto; }
    .output-panel {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        background-color: #f9f9f9;
    }
    .findings-section {
        margin: 20px 0;
        padding: 15px;
        border-left: 4px solid #2c3e50;
        background-color: #f8f9fa;
    }
    .error-message { color: #dc3545; }
    """

    with gr.Blocks(
        title="Market Research Assistant",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="gray"),
        css=custom_css
    ) as interface:
        gr.Markdown("""
        # 📊 Market Research Assistant
        Generate comprehensive market analysis reports with customizable focus areas and depth.
        """)

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
                        value=["Market Trends", "Competitor Analysis"],
                        label="Focus Areas"
                    )
                    export_format = gr.Radio(
                        choices=["markdown", "html", "pdf"],
                        value="markdown",
                        label="Export Format"
                    )

                submit_btn = gr.Button("🔍 Generate Report", variant="primary")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Intermediate Findings")
                intermediate_output = gr.Markdown(elem_classes="findings-section")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Final Report")
                final_report = gr.Markdown(elem_classes="output-panel")

        with gr.Row():
            file_path = gr.Textbox(label="Report Location")
            preview = gr.HTML(label="Preview")
            error_message = gr.Markdown(elem_classes="error-message")

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
                preview,
                error_message
            ]
        )

    return interface

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True)
