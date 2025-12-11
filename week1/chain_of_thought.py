import os
import re
from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 5

# TODO: Fill this in!
YOUR_SYSTEM_PROMPT = """
你是一位顶级的、严谨的问题解决专家和资深软件开发工程师。
你的主要目标是为用户提供问题的正确答案，并展示清晰的推理路径。

你必须严格遵循以下步骤和格式要求：

1. **强制思维链 (CoT):** 在提供最终答案之前，必须进行详细、逻辑清晰的逐步推理和分析。如果问题涉及编程、数学或多步逻辑，请将其分解为独立的步骤进行思考。
2. **结构化推理:** 所有的思考和分析过程**必须**封装在显式的 <thought> 和 </thought> XML 标签内。
3. **工具使用/精确性:** 如果问题涉及任何复杂的计算、代数求解或需要验证的逻辑，你必须使用 Markdown 格式的 Python 代码块（标签为 <tool_code>）来执行计算。请确保在 <tool_code> 块内运行的代码是完成计算任务的最佳方式，以保证结果的绝对精确性，而不是依赖心算。
4. **行为限制:** 你的回答必须专业、精确且专注于解决问题，避免任何不必要的寒暄或超出范围的信息。

请记住：你的输出必须始终包含 <thought> 标签（及其内容）、（如果需要）<tool_code> 标签，以及最终的 "Answer:" 行。
"""

USER_PROMPT = """
Solve this problem, then give the final answer on the last line as "Answer: <number>".

what is 3^{12345} (mod 100)?
"""


# For this simple example, we expect the final numeric answer only
EXPECTED_OUTPUT = "Answer: 43"


def extract_final_answer(text: str) -> str:
    """Extract the final 'Answer: ...' line from a verbose reasoning trace.

    - Finds the LAST line that starts with 'Answer:' (case-insensitive)
    - Normalizes to 'Answer: <number>' when a number is present
    - Falls back to returning the matched content if no number is detected
    """
    matches = re.findall(r"(?mi)^\s*answer\s*:\s*(.+)\s*$", text)
    if matches:
        value = matches[-1].strip()
        # Prefer a numeric normalization when possible (supports integers/decimals)
        num_match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if num_match:
            return f"Answer: {num_match.group(0)}"
        return f"Answer: {value}"
    return text.strip()


def test_your_prompt(system_prompt: str) -> bool:
    """Run up to NUM_RUNS_TIMES and return True if any output matches EXPECTED_OUTPUT.

    Prints "SUCCESS" when a match is found.
    """
    for idx in range(NUM_RUNS_TIMES):
        print(f"Running test {idx + 1} of {NUM_RUNS_TIMES}")
        response = chat(
            model="llama3.1:8b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT},
            ],
            options={"temperature": 0.3},
        )
        output_text = response.message.content
        final_answer = extract_final_answer(output_text)
        if final_answer.strip() == EXPECTED_OUTPUT.strip():
            print("SUCCESS")
            return True
        else:
            print(f"Expected output: {EXPECTED_OUTPUT}")
            print(f"Actual output: {final_answer}")
    return False


if __name__ == "__main__":
    test_your_prompt(YOUR_SYSTEM_PROMPT)


