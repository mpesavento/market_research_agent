# app.py
import gradio as gr
from langchain_core.messages import HumanMessage
from utils import AgentType
from workflow import MarketResearchWorkflow
import time
import markdown
from datetime import datetime
import pdfkit  # For PDF conversion
import os

def convert_to_pdf(markdown_text: str) -> str:
    """Convert markdown text to PDF and return the file path."""
    html = markdown.markdown(markdown_text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"reports/report_{timestamp}.pdf"
    os.makedirs("reports", exist_ok=True)
    pdfkit.from_string(html, pdf_path)
    return pdf_path

def save_markdown(markdown_text: str) -> str:
    """Save markdown text to file and return the file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = f"reports/report_{timestamp}.md"
    os.makedirs("reports", exist_ok=True)
    with open(md_path, 'w') as f:
        f.write(markdown_text)
    return md_path

def conduct_research(
    query: str,
    analysis_depth: str,
    focus_areas: list,
    progress=gr.Progress()
) -> tuple[str, str, str]:
    """
    Conduct market research and return results with progress updates.

    Returns:
        tuple: (report_text, pdf_path, markdown_path)
    """
    workflow = MarketResearchWorkflow()

    # Enhance query based on selected options
    enhanced_query = f"""{query}
    Please provide a {analysis_depth} analysis focusing on: {', '.join(focus_areas)}.
    """

    initial_state = {
        "messages": [HumanMessage(content=enhanced_query)],
        "next_agent": AgentType.MARKET_TRENDS.value,
        "research_data": {},
        "final_report": None
    }

    output_text = ["# Market Research Analysis Report\n"]
    output_text.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    output_text.append(f"## Analysis Parameters\n")
    output_text.append(f"- **Depth**: {analysis_depth}")
    output_text.append(f"- **Focus Areas**: {', '.join(focus_areas)}\n")

    try:
        for i, output in enumerate(workflow.run(initial_state)):
            agent_name = output["next_agent"].replace("_", " ").title()
            progress((i + 1)/4)

            output_text.append(f"\n### {agent_name} Analysis Status")
            output_text.append("✓ Completed")

            if output.get("final_report"):
                output_text.append("\n## Final Market Research Report\n")
                output_text.append(output["final_report"])
                progress(1.0)
                break

        # Combine all text and create downloadable versions
        final_text = "\n".join(output_text)
        pdf_path = convert_to_pdf(final_text)
        md_path = save_markdown(final_text)

        return final_text, pdf_path, md_path

    except Exception as e:
        error_msg = f"\n\n⚠️ Error during analysis: {str(e)}"
        return error_msg, None, None

# Create the Gradio interface
def create_interface():
    """Create and configure the Gradio interface."""

    # Custom CSS for better styling
    custom_css = """
    .container {
        max-width: 1000px;
        margin: auto;
    }
    .output-panel {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        background-color: #f9f9f9;
    }
    .download-btn {
        margin-top: 10px;
    }
    """

    # Example queries
    EXAMPLE_QUERIES = [
        "Analyze the market for fitness trackers focusing on sleep monitoring features",
        "Research the competitive landscape of high-end fitness wearables",
        "Investigate consumer preferences for fitness trackers in the $100-$200 range"
    ]

    with gr.Blocks(
        title="Market Research Assistant",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
        ),
        css=custom_css
    ) as interface:
        gr.Markdown("""
        # 📊 Wearable Fitness Tracker Market Research Assistant

        Generate comprehensive market analysis reports with customizable focus areas and depth.
        """)

        with gr.Row():
            with gr.Column(scale=2):
                input_text = gr.Textbox(
                    label="Research Query",
                    placeholder="Enter your market research query here...",
                    lines=3
                )

                with gr.Row():
                    analysis_depth = gr.Radio(
                        choices=["Basic", "Detailed", "Comprehensive"],
                        value="Detailed",
                        label="Analysis Depth",
                        interactive=True
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
                        label="Focus Areas",
                        interactive=True
                    )

                examples = gr.Examples(
                    examples=EXAMPLE_QUERIES,
                    inputs=input_text,
                    label="Example Queries"
                )

                submit_btn = gr.Button(
                    "🔍 Generate Report",
                    variant="primary"
                )

        with gr.Column():
            output = gr.Markdown(
                label="Research Results",
                value="Results will appear here...",
                elem_classes="output-panel"
            )

            with gr.Row():
                pdf_button = gr.File(
                    label="Download PDF Report",
                    elem_classes="download-btn"
                )
                md_button = gr.File(
                    label="Download Markdown Report",
                    elem_classes="download-btn"
                )

        submit_btn.click(
            fn=conduct_research,
            inputs=[
                input_text,
                analysis_depth,
                focus_areas
            ],
            outputs=[
                output,
                pdf_button,
                md_button
            ],
        )

    return interface

# Launch the interface
if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True)
