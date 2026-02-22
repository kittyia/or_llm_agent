import os
import copy
import json
import time
import argparse

import openai

from dotenv import load_dotenv

from utils import (
    is_number_string,
    extract_and_execute_python_code,
    eval_model_result,
)

# Allow tiny CLI override for OPENAI env vars: --OPENAI_API_KEY=... --OPENAI_API_BASE=...
import sys
for _arg in sys.argv[1:]:
    if _arg.startswith("--OPENAI_API_KEY="):
        os.environ["OPENAI_API_KEY"] = _arg.split("=", 1)[1]
    if _arg.startswith("--OPENAI_API_BASE="):
        os.environ["OPENAI_API_BASE"] = _arg.split("=", 1)[1]

# Load environment variables from .env file
load_dotenv()

# OpenAI API setup
openai_api_data = dict(
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_API_BASE")
)


# Initialize clients
openai_client = openai.OpenAI(
    api_key=openai_api_data['api_key'],
    base_url=openai_api_data['base_url'] if openai_api_data['base_url'] else None
)


def query_llm(messages: list, model_name="o3-mini", temperature=0.2)->str:
    """调用大模型接口，获取回复内容"""

    # Use OpenAI API
    response = openai_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content

def generate_or_code_solver(messages_backup:list, model_name:str, max_attempts:int):
    temp_messages = copy.deepcopy(messages_backup)

    gurobi_code = query_llm(temp_messages, model_name)
    print("【Python Gurobi 代码】:\n", gurobi_code)

    # 4. Code execution & fixes
    text = f"{gurobi_code}"
    attempt = 0
    while attempt < max_attempts:
        success, error_message = extract_and_execute_python_code(text)
        if success:
            messages_backup.append({"role": "assistant", "content": gurobi_code})
            return True, error_message, messages_backup

        print(f"\n尝试 {attempt + 1} 失败，正在请求LLM修复代码...\n")

        # Build repair request
        temp_messages.append({"role": "assistant", "content": gurobi_code})
        temp_messages.append({"role": "user", "content": f"Code execution encountered an error, error message is as follows:\n{error_message}\nPlease fix the code and provide the complete executable code again."})

        # Get the fixed code
        gurobi_code = query_llm(temp_messages, model_name)
        text = f"{gurobi_code}"

        print("\n接收到修复后的代码，准备再次执行...\n")
        attempt += 1
    # not add gurobi code
    messages_backup.append({"role": "assistant", "content": gurobi_code})
    print(f"达到最大尝试次数（{max_attempts}），仍无法成功执行代码。")
    return False, None, messages_backup

def or_llm_agent(problem_description, model_name="o3-mini", max_attempts=3):
    """
    Request Gurobi code solution from LLM and execute it, attempt to fix if it fails.

    Args:
        problem_description (str): User's problem description.
        model_name (str): LLM model name to use, default is "gpt-4".
        max_attempts (int): Maximum number of attempts, default is 3.

    Returns:
        tuple: (success: bool, best_objective: float or None, final_code: str)
    """
    # Initialize conversation history
    messages = [
        {"role": "system", "content": (
            "You are an operations research expert. Based on the optimization problem provided by the user, construct a mathematical model that effectively models the original problem using mathematical (linear programming) expressions."
            "Focus on obtaining a correct mathematical model expression without too much concern for explanations."
            "This model will be used later to guide the generation of Gurobi code, and this step is mainly used to generate effective linear scale expressions."
        )},
        {"role": "user", "content": problem_description}
    ]

    # 1. Generate mathematical model
    math_model = query_llm(messages, model_name)
    print("【数学模型】:\n", math_model)

    # 2. Validate mathematical model
    messages.append({"role": "assistant", "content": math_model})
    messages.append({"role": "user", "content": (
        "Please check if the above mathematical model matches the problem description. If there are errors, make corrections; if there are no errors, check if it can be optimized."
        "In any case, please output the final mathematical model again."
    )})

    validate_math_model = query_llm(messages, model_name)
    print("【验证之后的模型】:\n", validate_math_model)
    messages.append({"role": "assistant", "content": validate_math_model})

    # ------------------------------
    messages.append({"role": "user", "content": (
        "Based on the above mathematical model, write complete and reliable Python code using Gurobi to solve this operations research optimization problem."
        "The code should include necessary model construction, variable definitions, constraint additions, objective function settings, as well as solving and result output."
        "Output in the format ```python\n{code}\n```, without code explanations."
    )})
    # copy msg; solve; add the laset gurobi code
    is_solve_success, result, messages = generate_or_code_solver(messages, model_name,max_attempts)
    print(f'阶段结果: {is_solve_success}, {result}')
    if is_solve_success:
        if not is_number_string(result):
            print('!!【警告：没有有效解】!!')
            # no solution
            messages.append({"role": "user", "content": (
                "The current model resulted in *no feasible solution*. Please carefully check the mathematical model and Gurobi code for errors that might be causing the infeasibility."
                "After checking, please reoutput the Gurobi Python code."
                "Output in the format ```python\n{code}\n```, without code explanations."
            )})
            is_solve_success, result, messages = generate_or_code_solver(messages, model_name, max_attempts=1)
    else:
        print('!!【警告：达到最大尝试次数调试错误】!!')
        messages.append({"role": "user", "content": (
                "The model code still reports errors after multiple debugging attempts. Please carefully check if there are errors in the mathematical model."
                "After checking, please rebuild the Gurobi Python code."
                "Output in the format ```python\n{code}\n```, without code explanations."
            )})
        is_solve_success, result, messages = generate_or_code_solver(messages, model_name, max_attempts=2)

    return is_solve_success, result

def baseline_code_agent(user_question, model_name="o3-mini", max_attempts=3):
    """
    Request Gurobi code solution from LLM and execute it, attempt to fix if it fails.

    Args:
        user_question (str): User's problem description.
        model_name (str): LLM model name to use, default is "gpt-4".
        max_attempts (int): Maximum number of attempts, default is 3.

    Returns:
        tuple: (success: bool, best_objective: float or None, final_code: str)
    """
    # Initialize conversation history
    messages = [
        {"role": "system", "content": (
            "You are an operations research expert. Based on the optimization problem provided by the user, construct a mathematical model and write complete, reliable Python code using Gurobi to solve the operations research optimization problem."
            "The code should include necessary model construction, variable definitions, constraint additions, objective function settings, as well as solving and result output."
                "Output in the format ```python\n{code}\n```, without code explanations."
        )},
        {"role": "user", "content": user_question}
    ]

    # copy msg; solve; add the laset gurobi code
    gurobi_code = query_llm(messages, model_name)
    print("【Python Gurobi 代码】:\n", gurobi_code)
    text = f"{gurobi_code}"
    is_solve_success, result = extract_and_execute_python_code(text)

    print(f'阶段结果: {is_solve_success}, {result}')

    return is_solve_success, result

def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Run optimization problem solving with LLMs')
    parser.add_argument('--agent', action='store_true', 
                        help='Use the agent. If not specified, directly use the model to solve the problem')
    parser.add_argument('--model', type=str, default='o3-mini',
                        help='Model name to use for LLM queries. Use "claude-..." for Claude models.')
    parser.add_argument('--data_path', type=str, default='data/datasets/IndustryOR.json',
                        help='Path to the dataset JSON file (supports both JSONL and regular JSON formats)')
    # Minimal additional args to allow overriding OpenAI settings and enable math/debug flags
    parser.add_argument('--openai_api_key', type=str, default=None,
                        help='OpenAI API key (overrides environment variable)')
    parser.add_argument('--openai_api_base', type=str, default=None,
                        help='OpenAI API base URL (overrides environment variable)')
    parser.add_argument('--math', action='store_true', help='Generate math model first')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

def load_dataset(data_path):
    """
    Load dataset from either JSONL format (IndustryOR.json, BWOR.json) or regular JSON format
    """
    dataset = {}

    with open(data_path, 'r', encoding='utf-8') as f:
        # Try to detect format by reading first line
        first_line = f.readline().strip()
        f.seek(0)  # Reset file pointer

        if first_line.startswith('{"en_question"') or first_line.startswith('{"cn_question"'):
            # JSONL format (IndustryOR.json, BWOR.json)
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        # Convert to expected format
                        dataset_item = {
                            'question': item.get('en_question', item.get('cn_question', '')),
                            'answer': item.get('en_answer', item.get('cn_answer', '')),
                            'difficulty': item.get('difficulty', 'Unknown'),
                            'id': item.get('id', line_num - 1)
                        }
                        # Use id as string key
                        dataset[str(dataset_item['id'])] = dataset_item
                    except json.JSONDecodeError as e:
                        print(f"警告：无法解析第 {line_num} 行: {line}")
                        continue
        else:
            # Regular JSON format (legacy)
            dataset = json.load(f)

    return dataset

if __name__ == "__main__":
    args = parse_args()

    # If user provided openai args, set environment and re-create client (minimal, non-invasive)
    if args.openai_api_key:
        os.environ['OPENAI_API_KEY'] = args.openai_api_key
    if args.openai_api_base:
        os.environ['OPENAI_API_BASE'] = args.openai_api_base

    # Re-create openai_client using possibly-updated environment values
    openai_api_data = dict(
        api_key = os.getenv("OPENAI_API_KEY"),
        base_url = os.getenv("OPENAI_API_BASE")
    )
    openai_client = openai.OpenAI(
        api_key=openai_api_data['api_key'],
        base_url=openai_api_data['base_url'] if openai_api_data['base_url'] else None
    )

    dataset = load_dataset(args.data_path)

    model_name = args.model

    pass_count = 0
    correct_count = 0
    error_datas = []
    start_time = time.time()
    for i, d in dataset.items():
        print(f"程序运行时长: {time.time() - start_time:.2f} 秒，正在运行第 {i} 个问题")
        user_question, answer = d['question'], d['answer']
        print(user_question)
        print('-------------')

        if args.agent:
            is_solve_success, llm_result = or_llm_agent(user_question, model_name)
        else:
            is_solve_success, llm_result = baseline_code_agent(user_question, model_name)

        if is_solve_success:
            print(f"成功执行代码，最优解值:  {llm_result}")
        else:
            print("执行代码失败。")
        print('------------------')
        pass_flag, correct_flag = eval_model_result(is_solve_success, llm_result, answer)

        pass_count += 1 if pass_flag else 0
        correct_count += 1 if correct_flag else 0

        if not pass_flag or not correct_flag:
            error_datas.append(i)

        print(f'求解结果: {is_solve_success}, LLM输出: {llm_result}, 参考答案: {answer}')
        print(f'[最终结果] 运行成功: {pass_flag}, 求解正确: {correct_flag}')

    print(f'[总共 {len(dataset)}] 运行成功数量: {pass_count}, 求解正确数量: {correct_count}')
    print(f'[总共失败 {len(error_datas)}] 错误数据编号: {error_datas}')

    end_time = time.time()
    print(f'总耗时: {end_time - start_time:.2f} 秒')
