# -*- coding: utf-8 -*-
"""后端冒烟测试：路由、缺密钥报错、桩客户端跑通双 Agent 流水线。

用法（在 backend/ 目录下）:
    python smoke_test.py
"""
import json

from fastapi.testclient import TestClient

import agents
import main

client = TestClient(main.app)
routes = sorted({r.path for r in main.app.routes if hasattr(r, "path")})
print("路由:", routes)
assert "/api/generate" in routes and "/api/fix" in routes and "/api/health" in routes

r = client.get("/api/health")
print("GET /api/health ->", r.status_code, r.json())
assert r.status_code == 200 and r.json()["status"] == "ok"

r = client.post("/api/generate", json={"prompt": "傅里叶变换"})
print("POST /api/generate (无密钥) ->", r.status_code, str(r.json())[:120])
assert r.status_code == 500
assert "DEEPSEEK_API_KEY" in r.json()["detail"]

r = client.post("/api/generate", json={})
print("POST /api/generate (缺字段) ->", r.status_code)
assert r.status_code == 422


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, outer):
        self.outer = outer

    def create(self, **kwargs):
        self.outer.calls.append(kwargs)
        system = kwargs["messages"][0]["content"]
        if "计算物理学教授" in system:
            return _Resp(json.dumps({
                "title": "傅里叶合成方波",
                "subtitle": "多个旋转圆叠加出方波",
                "formula_latex": "f(t) = 4/π Σ sin((2k-1)ωt)/(2k-1)",
                "intuition_challenge": "圆的数量趋近无穷时会怎样？",
                "controls": [{"id": "n", "label": "圆的数量", "min": 1, "max": 15,
                              "step": 1, "default": 3, "description": "越多越接近方波"}],
                "visual_spec": {"entities": "旋转圆 + 轨迹"},
            }, ensure_ascii=False))
        if "创意前端架构师" in system:
            return _Resp("```html\n<!DOCTYPE html><html><body><canvas></canvas></body></html>\n```")
        return _Resp("```html\n<!DOCTYPE html><html><body>fixed</body></html>\n```")


class _Chat:
    def __init__(self, outer):
        self.completions = _Completions(outer)


class StubClient:
    def __init__(self):
        self.calls = []
        self.chat = _Chat(self)


stub = StubClient()
agents.get_client = lambda: stub  # type: ignore[assignment]

out = agents.generate_lab("演示傅里叶级数合成方波")
print("plan.title =", out["plan"]["title"])
print("plan.controls =", len(out["plan"]["controls"]))
print("html 是否已剥离代码围栏:", out["html"].startswith("<!DOCTYPE html>") and "```" not in out["html"])
assert out["plan"]["title"] == "傅里叶合成方波"
assert out["html"].startswith("<!DOCTYPE html>") and "```" not in out["html"]
assert len(stub.calls) == 2, stub.calls

fixed = agents.fix_lab_code("<html>broken</html>", "ReferenceError: x is not defined")
print("fix 输出:", fixed[:60])
assert fixed.startswith("<!DOCTYPE html>")

# 验证 JSON 围栏容错
assert agents.clean_json_output('```json\n{"a": 1}\n```') == {"a": 1}
print("\n后端冒烟测试全部通过")
