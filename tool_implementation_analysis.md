# Claude Code 项目的 Tool 实现机制详解

## 🔧 核心概念

Tool（工具）是 AI Agent 与外部世界交互的桥梁。Claude 模型通过调用 tools 来执行实际操作，而不仅仅是生成文本。

## 📊 Tool 实现的完整流程

```
用户输入 → Claude API (with tools) → 模型决策
                                         ↓
                                    返回 tool_use
                                         ↓
                                    执行工具函数
                                         ↓
                                    返回结果给模型
                                         ↓
                                    模型继续决策
                                         ↓
                                    最终文本响应
```

## 1️⃣ Tool 定义格式

### 基本结构（JSON Schema）
```python
{
    "name": "tool_name",           # 工具名称
    "description": "what it does",  # 工具描述（供模型理解）
    "input_schema": {               # 参数定义（JSON Schema）
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "parameter description"
            },
            "param2": {
                "type": "integer",
                "description": "optional parameter"
            }
        },
        "required": ["param1"]      # 必需参数列表
    }
}
```

### 实际例子：bash 工具
```python
{
    "name": "bash",
    "description": "Run a shell command. Use for: ls, find, grep, git, npm, python, etc.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute"
            }
        },
        "required": ["command"]
    }
}
```

## 2️⃣ Tool 调用解析

### Claude API 响应结构
```python
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,        # 传入工具列表
    max_tokens=8000
)

# response.content 包含混合内容
for block in response.content:
    if block.type == "text":
        # 普通文本输出
        print(block.text)
    
    if block.type == "tool_use":
        # 工具调用请求
        # block.id: 唯一标识符
        # block.name: 工具名称
        # block.input: 参数字典
```

### 关键判断：是否继续循环
```python
if response.stop_reason == "tool_use":
    # 继续执行工具
else:
    # 任务完成，返回最终响应
```

## 3️⃣ Tool 执行实现

### 分发器模式（v1-v4）
```python
def execute_tool(name: str, args: dict) -> str:
    """工具执行分发器"""
    if name == "bash":
        return run_bash(args["command"])
    
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    
    if name == "write_file":
        return run_write(args["path"], args["content"])
    
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    
    # v2: 添加 TodoWrite
    if name == "TodoWrite":
        return todo_manager.update(args["items"])
    
    # v3: 添加 Task（递归调用子Agent）
    if name == "Task":
        return run_subagent(args["description"], args["prompt"], args["agent_type"])
    
    # v4: 添加 Skill（知识注入）
    if name == "Skill":
        return load_skill(args["skill"])
    
    return f"Unknown tool: {name}"
```

### 具体工具实现示例

#### bash 工具
```python
def run_bash(command: str) -> str:
    """执行shell命令"""
    # 安全检查
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=60          # 60秒超时
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000]   # 限制输出大小
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"
```

#### read_file 工具
```python
def run_read(path: str, limit: int = None) -> str:
    """读取文件内容"""
    try:
        # 路径安全检查
        fp = safe_path(path)  
        text = fp.read_text()
        
        # 支持行数限制
        if limit:
            lines = text.splitlines()[:limit]
            lines.append(f"... ({len(text.splitlines()) - limit} more lines)")
            return "\n".join(lines)[:50000]
        
        return text[:50000]
    except Exception as e:
        return f"Error: {e}"
```

## 4️⃣ Tool 结果返回

### 标准格式
```python
results = []
for tc in tool_calls:
    output = execute_tool(tc.name, tc.input)
    
    # 构建工具结果
    results.append({
        "type": "tool_result",
        "tool_use_id": tc.id,      # 必须匹配调用ID
        "content": output           # 字符串结果
    })

# 添加到消息历史
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": results})
```

## 5️⃣ 核心 Agent 循环

```python
def agent_loop(messages: list) -> list:
    """完整的Agent循环"""
    while True:
        # 1. 调用模型
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000
        )
        
        # 2. 检查是否有工具调用
        if response.stop_reason != "tool_use":
            # 没有工具调用，任务完成
            messages.append({"role": "assistant", "content": response.content})
            return messages
        
        # 3. 执行所有工具调用
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        results = []
        
        for tc in tool_calls:
            output = execute_tool(tc.name, tc.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": output
            })
        
        # 4. 将结果添加到历史，继续循环
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})
```

## 6️⃣ 高级特性演化

### v0 → v1: 基础工具集
- 单工具(bash) → 四工具(bash, read, write, edit)
- 添加安全措施（路径验证、命令过滤）

### v1 → v2: 有状态工具
```python
# TodoManager 维护状态
class TodoManager:
    def __init__(self):
        self.todos = []
    
    def update(self, items):
        self.todos = items
        return self.render()
```

### v2 → v3: 递归工具（子Agent）
```python
def run_subagent(description, prompt, agent_type):
    """工具可以生成新的Agent实例"""
    tools = AGENT_REGISTRY[agent_type]  # 不同类型不同工具集
    messages = [{"role": "user", "content": prompt}]
    return agent_loop(messages, tools)  # 递归调用
```

### v3 → v4: 知识注入工具
```python
def load_skill(skill_name):
    """动态加载领域知识"""
    skill_path = Path("skills") / skill_name / "SKILL.md"
    content = skill_path.read_text()
    
    # 关键：作为 tool_result 返回，保持缓存
    return f"Skill '{skill_name}' loaded:\n\n{content}"
```

## 🎯 关键设计原则

### 1. **简单性**
- 工具定义使用标准 JSON Schema
- 执行逻辑是简单的函数调用
- 结果始终是字符串

### 2. **安全性**
- 路径沙箱（防止越权访问）
- 命令过滤（阻止危险操作）
- 超时限制（防止挂起）
- 输出截断（防止上下文溢出）

### 3. **可扩展性**
- 添加新工具只需：
  1. 定义 JSON Schema
  2. 实现执行函数
  3. 添加到分发器

### 4. **缓存优化**
- v4 的创新：技能内容作为 tool_result 而非 system prompt
- 保持系统提示不变，维持缓存命中

### 5. **递归能力**
- 工具可以调用其他工具
- 工具可以生成新的 Agent
- 实现了任务分解和并行执行

## 💡 核心洞察

**"Model as Agent"** - 模型是决策者，代码只是执行者：

1. **模型决定**：调用哪个工具、何时调用、调用顺序
2. **代码执行**：忠实执行模型的决策，返回结果
3. **循环迭代**：直到模型认为任务完成

这种设计让 AI Agent 的能力完全取决于模型的智能，而不是代码的复杂度。代码保持简单，让模型发挥主导作用。

## 🚀 实用价值

这个实现模式已经在生产环境中得到验证：
- **Claude Code**（Anthropic官方）
- **Cursor IDE**
- **Kode CLI**
- **各种 AI 编程助手**

都使用相同的核心模式：工具定义 → 模型调用 → 执行返回 → 循环继续。

理解这个机制后，你可以：
1. 自定义工具扩展 Agent 能力
2. 优化工具实现提高效率
3. 设计新的工具模式（如v4的技能系统）
4. 构建自己的 AI Agent 系统