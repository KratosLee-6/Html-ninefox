"""Html九尾狐 Python API：生成后提交一次反馈。"""
from pathlib import Path

from htmlninefox import pipeline

result = pipeline.run_expert(
    "做一个 SaaS 落地页，品牌狐构，目标用户是设计师",
    output="./output",
    intent_override="landing",
    quiet_llm=True,
)
project = Path(result["work"])
feedback = pipeline.run_feedback(str(project), "颜色再深一点，标题大一点", revise=True)
print({"project": str(project), "revision": feedback.get("revision"), "ok": feedback.get("ok")})
