"""
结构化 Prompt 构建器
接收各层内容，按 SillyTavern 风格组装为 JSON messages 数组

每层是一个 Layer 对象，包含：
  - role: "system" | "user"
  - layer_id: 唯一标识（用于 debug 和排序）
  - label: 中文描述
  - content: 文本内容
  - active: 是否启用（False 则跳过）
"""

from typing import Optional


class Layer:
    def __init__(self, role: str, layer_id: str, label: str,
                 content: str, active: bool = True):
        self.role = role
        self.layer_id = layer_id
        self.label = label
        self.content = content
        self.active = active

    def to_message(self) -> Optional[dict]:
        """转换为 OpenAI messages 格式，附带元数据"""
        if not self.active or not self.content or not self.content.strip():
            return None
        return {
            "role": self.role,
            "content": self.content.strip(),
            "_layer": self.layer_id,
            "_label": self.label,
        }

    def __repr__(self):
        return f"<Layer {self.layer_id} [{self.role}] active={self.active}>"


def build_messages(layers: list[Layer]) -> list[dict]:
    """
    组装 messages 数组
    按添加顺序保持，移除不活跃和空层
    """
    messages = []
    for layer in layers:
        msg = layer.to_message()
        if msg:
            messages.append(msg)
    return messages


def build_system_prompt(
    base_prompt: str,
    extra_prompt: Optional[str] = None,
    learning_context: Optional[str] = None,
    kb_context: Optional[str] = None,
    fact_check_context: Optional[str] = None,
) -> list[dict]:
    """
    快捷组装：按标准顺序生成 system messages
    顺序：
      0. base_system    (必有)
      1. extra_prompt   (可选，用户配置)
      2. learning_inject(可选，自学习)
      3. kb_context     (可选，知识库)
      4. fact_check     (可选，联网核查)
    """
    layers = [
        Layer("system", "base_system", "系统基础指令集",
              base_prompt, active=True),
        Layer("system", "extra_prompt", "用户自定义补充要求",
              f"以下是用户补充的分析要求，请在不违反基础规则的前提下参考：\n{extra_prompt}",
              active=bool(extra_prompt)),
        Layer("system", "learning_inject", "历史经验参考",
              learning_context,
              active=bool(learning_context)),
        Layer("system", "kb_context", "知识库预检结果",
              kb_context,
              active=bool(kb_context)),
        Layer("system", "fact_check", "联网事实核查结果",
              fact_check_context,
              active=bool(fact_check_context)),
    ]
    return build_messages(layers)


def build_user_input(
    product_text: Optional[str],
    url: Optional[str],
    source_type: Optional[str] = None,
) -> list[dict]:
    """生成用户输入层"""
    from services.ai_analyzer import _build_user_prompt
    content = _build_user_prompt(product_text, url, source_type)
    if not content:
        return []
    return [{
        "role": "user",
        "content": content,
        "_layer": "user_input",
        "_label": "用户商品信息",
    }]
