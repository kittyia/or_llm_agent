import re
import csv


def parse_log_to_csv(log_file_path, output_csv_path):
    """
    解析日志文件，提取每个问题的运行信息并生成CSV。
    改进：自动识别最后一个问题的运行时长（通过程序总耗时）
    """
    # 存储所有问题的数据
    problems = []

    # 读取整个日志文件
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取程序总耗时（在文件末尾）
    total_time_match = re.search(r'总耗时:\s*([\d.]+)\s*秒', content)
    total_time = float(total_time_match.group(1)) if total_time_match else None

    # 按问题分割（使用“开始运行第 X 个问题”作为分隔标记）
    problem_starts = list(re.finditer(
        r'程序运行时长: ([\d.]+) 秒，开始运行第 (\d+) 个问题',
        content
    ))

    for i, start_match in enumerate(problem_starts):
        current_problem_num = int(start_match.group(2))
        current_start_time = float(start_match.group(1))

        # 确定该问题的结束时间
        if i < len(problem_starts) - 1:
            # 不是最后一个问题：用下一个问题的开始时间
            next_start_time = float(problem_starts[i + 1].group(1))
            duration = round(next_start_time - current_start_time, 2)
        else:
            # 是最后一个问题：用程序总耗时减去当前开始时间
            if total_time is not None:
                duration = round(total_time - current_start_time, 2)
            else:
                duration = None  # 如果找不到总耗时，就保持None

        # 确定该问题的内容区间
        start_pos = start_match.end()
        if i < len(problem_starts) - 1:
            end_pos = problem_starts[i + 1].start()
        else:
            end_pos = len(content)

        problem_content = content[start_pos:end_pos]

        # 从该问题的内容中提取运行成功和求解正确信息
        final_result_match = re.search(r'\[最终结果\] 运行成功: (True|False), 求解正确: (True|False)', problem_content)
        if final_result_match:
            run_success = final_result_match.group(1) == 'True'
            solve_correct = final_result_match.group(2) == 'True'
        else:
            # 如果没有找到最终结果行，尝试找阶段结果行
            stage_result_match = re.search(r'阶段结果: (True|False), ([\d.]+|None)', problem_content)
            if stage_result_match:
                run_success = stage_result_match.group(1) == 'True'
                solve_correct = False
            else:
                run_success = False
                solve_correct = False

        problems.append({
            'problem_num': current_problem_num,
            'run_success': run_success,
            'solve_correct': solve_correct,
            'duration': duration
        })

    # 写入CSV文件
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['问题序号', '运行是否成功', '求解是否正确', '运行时长(秒)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for prob in problems:
            writer.writerow({
                '问题序号': prob['problem_num'],
                '运行是否成功': prob['run_success'],
                '求解是否正确': prob['solve_correct'],
                '运行时长(秒)': prob['duration'] if prob['duration'] is not None else 'N/A'
            })

    print(f"已成功解析 {len(problems)} 个问题，结果已保存到 {output_csv_path}")
    if total_time:
        print(f"程序总运行时长: {total_time} 秒")

    # 显示统计信息
    run_success_count = sum(1 for p in problems if p['run_success'])
    solve_correct_count = sum(1 for p in problems if p['solve_correct'])
    print(f"运行成功: {run_success_count}/{len(problems)}")
    print(f"求解正确: {solve_correct_count}/{len(problems)}")

    # 显示前几行作为预览
    print("\n预览（前5行）:")
    for prob in problems[:5]:
        print(f"问题 {prob['problem_num']}: 运行成功={prob['run_success']}, "
              f"求解正确={prob['solve_correct']}, 时长={prob['duration']}秒")


# 使用示例
if __name__ == "__main__":
    baseline_log_file = "baseline.log"  # baseline
    agent_log_file = "agent_mode.log"  # agent
    baseline_csv = "baseline_results.csv"
    agent_csv = "agent_mode_results.csv"

    parse_log_to_csv(baseline_log_file, baseline_csv)
    parse_log_to_csv(agent_log_file, agent_csv)