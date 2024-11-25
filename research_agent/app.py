# app.py
import gradio as gr
from langchain_core.messages import HumanMessage
import time
import markdown
from datetime import datetime
import pdfkit
from pathlib import Path
import os
import json
from typing import Optional

from workflow import build_research_graph, MarketResearchState


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
    try:
        # Define depth expectations
        depth_definitions = {
            "Basic": """
                - Provide a high-level overview of key points
                - Focus on main trends and obvious market leaders
                - Include essential statistics and basic market insights
                - Typical length: 2-3 key points per focus area""",
            "Detailed": """
                - Provide in-depth analysis with specific examples
                - Include relevant market statistics and data points
                - Analyze both major and emerging players
                - Compare and contrast different market segments
                - Typical length: 4-6 detailed points per focus area""",
            "Comprehensive": """
                - Provide extensive analysis with detailed insights
                - Include comprehensive market statistics and trend analysis
                - Cover major players, emerging companies, and niche segments
                - Analyze historical trends and future projections
                - Include specific examples, case studies, and market data
                - Typical length: 7+ detailed points per focus area"""
        }

        # Define focus area expectations
        focus_area_definitions = {
            "Market Trends": "Analysis of current market direction, growth patterns, emerging technologies, and shifting dynamics",
            "Competitor Analysis": "Detailed review of major players, market share, competitive advantages, and strategic positioning",
            "Consumer Behavior": "Understanding of customer preferences, buying patterns, demographic insights, and user needs",
            "Technology Features": "Evaluation of current and emerging technologies, technical specifications, and innovation trends",
            "Pricing Strategy": "Analysis of market pricing models, cost structures, value propositions, and pricing trends"
        }

        # Format the enhanced query
        enhanced_query = f"""Conduct a {analysis_depth.lower()} market analysis regarding: {query}

Analysis Depth Requirements ({analysis_depth}):
{depth_definitions[analysis_depth]}

Focus Areas (provide detailed analysis for each):
{chr(10).join(f'- {area}: {focus_area_definitions[area]}' for area in focus_areas)}

Please structure your analysis to clearly address each focus area separately, maintaining the specified depth level throughout the report."""

        graph = build_research_graph()
        initial_state: MarketResearchState = {
            "messages": [HumanMessage(content=enhanced_query)],
            "research_data": {},
            "next_agent": "market_trends",
            "final_report": None
        }

        # Use a dictionary to store intermediate findings, keyed by agent name
        intermediate_findings_dict = {}

        for output in graph.stream(initial_state):
            if isinstance(output, dict):
                agent_name = next(iter(output))
                agent_data = output[agent_name]

                progress((len(intermediate_findings_dict) + 1)/4)

                if isinstance(agent_data, dict) and "research_data" in agent_data:
                    for data_agent, data in agent_data["research_data"].items():
                        if "findings" in data:
                            # Store/update findings in dictionary instead of appending to list
                            intermediate_findings_dict[data_agent] = f"### {data_agent.replace('_', ' ').title()}\n\n{data['findings']}\n\n---\n"

                if isinstance(agent_data, dict) and agent_data.get("final_report"):
                    final_report_text = agent_data["final_report"]
                    progress(1.0)
                    break

        # Convert dictionary to list in desired order (if order matters)
        intermediate_findings = [
            intermediate_findings_dict[agent]
            for agent in ["market_trends", "competitor", "consumer"]
            if agent in intermediate_findings_dict
        ]

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

    /* Info icon styling */
    .info-icon {
        display: inline-block;
        margin-left: 5px;
        color: #666;
        cursor: help;
    }

    /* Tooltip container styling */
    .gr-form > div[class*="row"] {
        position: relative;
    }
    """

    # Define tooltips using our existing definitions
    depth_tooltips = {
        "Basic": "High-level overview with 2-3 key points per focus area",
        "Detailed": "In-depth analysis with 4-6 detailed points per focus area",
        "Comprehensive": "Extensive analysis with 7+ detailed points per focus area, including case studies"
    }

    focus_area_tooltips = {
        "Market Trends": "Analysis of current market direction, growth patterns, emerging technologies, and shifting dynamics",
        "Competitor Analysis": "Detailed review of major players, market share, competitive advantages, and strategic positioning",
        "Consumer Behavior": "Understanding of customer preferences, buying patterns, demographic insights, and user needs",
        "Technology Features": "Evaluation of current and emerging technologies, technical specifications, and innovation trends",
        "Pricing Strategy": "Analysis of market pricing models, cost structures, value propositions, and pricing trends"
    }

    export_format_tooltips = {
        "markdown": "Plain text format with basic formatting",
        "html": "Web-friendly format with styling",
        "pdf": "Professional document format suitable for printing"
    }

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
                    lines=3,
                    info="Enter a specific market research question or topic to analyze"
                )

                with gr.Row():
                    analysis_depth = gr.Radio(
                        choices=["Basic", "Detailed", "Comprehensive"],
                        value="Detailed",
                        label="Analysis Depth",
                        info="\n".join(f"{k}: {v}" for k, v in depth_tooltips.items())
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
                        label="Focus Areas",
                        info="\n".join(f"{k}: {v}" for k, v in focus_area_tooltips.items())
                    )
                    export_format = gr.Radio(
                        choices=["markdown", "html", "pdf"],
                        value="markdown",
                        label="Export Format",
                        info="\n".join(f"{k}: {v}" for k, v in export_format_tooltips.items())
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
