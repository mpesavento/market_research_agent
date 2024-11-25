import gradio as gr
from datetime import datetime
import markdown
from research_agent.workflow import create_market_research_orchestrator

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
            - "pdf": PDF document with formatting (not yet implemented)
        progress (gr.Progress, optional): Gradio progress bar instance for updating UI.
            Automatically provided by Gradio.

    Returns:
        tuple[str, str, str, str, str]: A tuple containing:
            - intermediate_findings: Markdown formatted string of findings from each specialized agent
            - final_report: Synthesized final report text from the orchestrator
            - file_path: Path to the saved report file in reports directory
            - preview_content: HTML preview of the report (if format is html)
            - error_message: Error description if any occurred, empty string otherwise

    Raises:
        ValueError: If query is empty or invalid
        RuntimeError: If research workflow fails to generate a report
        Exception: For other errors during research or report generation

    Example:
        >>> findings, report, path, preview, error = conduct_research(
        ...     query="Analyze the electric vehicle market in Europe",
        ...     analysis_depth="Detailed",
        ...     focus_areas=["Market Trends", "Competitor Analysis"],
        ...     export_format="markdown"
        ... )
    """
    try:
        # Format the enhanced query
        enhanced_query = enhance_query(query, analysis_depth, focus_areas)

        # Create a status callback that updates the Gradio progress bar
        def status_callback(message: str):
            # Map specific messages to progress percentages
            progress_map = {
                "Starting market research workflow...": 0.1,
                "🔍 Analyzing market trends...": 0.2,
                "🏢 Analyzing competitors...": 0.4,
                "👥 Analyzing consumer behavior...": 0.6,
                "📝 Generating final report...": 0.8,
                "Saving research outputs...": 0.9,
                "Research workflow complete!": 1.0
            }
            # Get progress value or default to current value
            progress_value = progress_map.get(message, None)
            if progress_value is not None:
                progress(progress_value, desc=message)

        # Create and run the research orchestrator with status updates
        orchestrator = create_market_research_orchestrator(status_callback=status_callback)
        result = orchestrator.run_research(enhanced_query)

        # Format intermediate findings from agent outputs
        intermediate_findings = ""
        for agent_name, output in result["agent_outputs"].items():
            if "findings" in output:
                intermediate_findings += f"\n### {agent_name.replace('_', ' ').title()}\n"
                intermediate_findings += output["findings"]
                intermediate_findings += "\n---\n"

        # Convert and save in requested format
        file_path, preview_content, error = save_report(
            result["final_report"],
            export_format
        )

        return (
            intermediate_findings,
            result["final_report"],
            file_path or "",
            preview_content or "",
            error or ""
        )

    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        return "", "", "", "", error_msg

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
                gr.Markdown("### Intermediate Findings", elem_classes="markdown-text")
                intermediate_output = gr.Markdown(
                    elem_classes="findings-section markdown-content",
                    show_label=False
                )

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Final Report", elem_classes="markdown-text")
                final_report = gr.Markdown(
                    elem_classes="output-panel markdown-content",
                    show_label=False
                )

        with gr.Row():
            file_path = gr.Textbox(
                label="Report Location",
                show_label=True,
                container=True
            )
            preview = gr.HTML(
                label="Preview",
                show_label=True
            )
            error_message = gr.Markdown(
                elem_classes="error-message",
                show_label=False
            )

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
