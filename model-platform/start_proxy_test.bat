@echo off
set NO_PROXY=*
set PYTHONUTF8=1
set LITELLM_MASTER_KEY=sk-my-master-key-1234
set LITELLM_LOCAL_MODEL_COST_MAP=True
set MINIMAX_API_KEY=sk-cp-Bb9XSvcewcN_vUseXqAPCqTwMPJ8eOZ0-L1XXq8ghZ8yjGeajL5mHnCnlRJxOdPouWqz1rsSTv2HZdSnGhMS5cGpETeF8-7895F08RnplgM2dYD66TGPlsM
set DEEPSEEK_API_KEY=sk-a806fa36e05c417c915d07d0f8aff7f3
set ZAI_API_KEY=fc467de3d0b848f092251bff43892c3e.9E6MRwU25hQmJVpl
echo [%date% %time%] Starting LiteLLM Proxy...
C:\litellm-env\Scripts\litellm.exe --config d:\Desktop\Test\MultiModel\model-platform\config.yaml --port 4800
