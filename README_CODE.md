Baseline 运行命令：
```bash
nohup python3.12 or_llm_evaluation.py --openai_api_key "***" --openai_api_base "https://1yvxf19722895.vicp.fun/v1" --model "Qwen/Qwen3-8B" --data_path "data/datasets/IndustryOR.json" > baseline.log 2>&1 &

```

or_llm_agent 运行命令：
```bash
nohup python3.12 or_llm_evaluation.py --openai_api_key "***" --openai_api_base "https://1yvxf19722895.vicp.fun/v1" --model "Qwen/Qwen3-8B" --agent --data_path "data/datasets/IndustryOR.json" > agent_mode.log 2>&1 &
```
