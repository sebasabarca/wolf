import anthropic
from tools import analyze_stock, get_company_tickers
from dotenv import load_dotenv
from createMarkupFile import save_analysis
import json

load_dotenv()

client = anthropic.Anthropic()

tools = [
    {
        "name": "search_stock_ticker",
        "description": "Obtain a companies ticker symbol using its name. ",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "A company name that has a valid ticker symbol."
                }
            },
            "required": ["company_name"],
        }
    },
    {
        "name": "analyze_stock",
        "description": (
            "Analyze a stock's business fundamentals, price history, "
            "recent news, and upcoming earnings risks. "
            "Use when the user requests a 30-day stock analysis. "
            "Pass the stock's ticker symbol as the parameter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol of the stock that will be analyzed."
                }
            },
            "required": ["ticker"],
        }
    }
]

def create_message(role, content):
    return [{"role": role, "content": content }]

def get_agent_answer(messages):
    return client.messages.create(
    model="claude-opus-5-5",
    max_tokens=4096,
    tools=tools,
    tool_choice={"type": "auto", "disable_parallel_tool_use": True},
    messages=messages,
)

def get_tools_used(response):
    return next(
        (block for block in response.content if block.type == "tool_use"),
        None
    )


def generate_analysis(prompt):
    messages = create_message("user", prompt)
    response = get_agent_answer(messages)

    max_steps = 10
    steps = 0

    while response.stop_reason == "tool_use" and steps < max_steps:
        tool = get_tools_used(response)

        if tool is None:
            return "Claude requested a tool but none was found."

        print(f"Executing: {tool.name}({tool.input})")

        try:
            if tool.name == "analyze_stock":
                tool_result = analyze_stock(tool.input["ticker"])

            elif tool.name == "search_stock_ticker":
                tool_result = get_company_tickers(
                    tool.input["company_name"]
                )

            else:
                tool_result = {
                    "error": f"Unknown tool: {tool.name}"
                }

        except Exception as error:
            tool_result = {"error": str(error)}

        messages += create_message(
            "assistant",
            response.content
        )

        messages += create_message(
            "user",
            [{
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": json.dumps(
                    tool_result,
                    default=str,
                    allow_nan=False
                )
            }]
        )

        steps += 1
        response = get_agent_answer(messages)

    # Claude finished its analysis
    if response.stop_reason == "end_turn":
        final_text = "\n".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

        if not final_text.strip():
            return "Claude returned no text."

        file_path = save_analysis(final_text)
        return f"Analysis saved to: {file_path}"

    if response.stop_reason == "max_tokens":
        return "Claude reached the token limit before finishing."

    if steps >= max_steps and response.stop_reason == "tool_use":
        return "Wolf reached its maximum number of tool calls."

    return f"Unexpected stop reason: {response.stop_reason}"



def main():
    print("Welcome to Wolf - AI Stock Research Agent")
    print("Enter a stock research question.\n")

    prompt = input("Wolf > ").strip()

    if not prompt:
        print("Please enter a valid question.")
        return

    print("\nAnalyzing your request...\n")

    result = generate_analysis(prompt)
    print(result)


if __name__ == "__main__":
    main()