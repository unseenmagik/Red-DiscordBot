@Echo off
chcp 65001
:Start

python main.py
timeout 3

goto Start