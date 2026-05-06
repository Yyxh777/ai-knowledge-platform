# AI 知识助手 - 部署和使用指南

## 🎯 功能介绍

已完成的改造：
1. ✅ FastAPI 支持 WebSocket 实时通信
2. ✅ 流式响应，类似 ChatGPT 的打字效果
3. ✅ 仿 ChatGPT 的现代化前端界面
4. ✅ SpringBoot 集成，统一访问入口
5. ✅ 基于 Milvus 向量数据库的 RAG 问答

## 📋 前置条件

1. **Milvus 向量数据库**运行在 `localhost:19530`
2. **Python FastAPI 服务**运行在 `localhost:8000`
3. **SpringBoot 服务**运行在配置的端口（例如 `8080`）

## 🚀 启动步骤

### 1. 启动 Milvus（如果还没启动）

```bash
docker run -d --name milvus-standalone -p 19530:19530 milvusdb/milvus:latest
```

### 2. 启动 FastAPI 服务

```bash
cd python-ai-service
conda activate langchainv1
fastapi dev main.py
```

FastAPI 将运行在 `http://localhost:8000`

### 3. 启动 SpringBoot 服务

```bash
cd java-service
mvn spring-boot:run
# 或使用 IDE 运行
```

SpringBoot 将运行在配置的端口（通常是 `8080` 或 `80`）

## 🌐 访问方式

启动所有服务后，可以通过以下方式访问聊天页面：

### 方式 1: 直接访问静态页面
```
http://localhost:8080/chat.html
```

### 方式 2: 通过控制器跳转
```
http://localhost:8080/ai/chat-page
或
http://localhost:8080/ai/
```

## 📡 WebSocket 连接

前端页面会自动连接到 FastAPI 的 WebSocket 端点：
```
ws://localhost:8000/ai/ws/chat
```

## 🎨 界面功能

### 主要特性
- ✨ 仿 ChatGPT 的深色主题界面
- 💬 实时流式回复（打字机效果）
- 🔄 自动重连机制
- 📝 支持多行输入（Shift + Enter）
- 🎯 预设问题快速发送
- 🧹 清空对话重新开始
- 📊 实时连接状态显示

### 快捷键
- `Enter` - 发送消息
- `Shift + Enter` - 换行

## 🔧 配置修改

### 修改 FastAPI 端口
如果 FastAPI 不在 `8000` 端口，需要修改：

**文件**: `java-service/src/main/resources/static/chat.html`

```javascript
// 修改第 286 行
const WS_URL = 'ws://localhost:你的端口/ai/ws/chat';
```

### 修改 SpringBoot 端口
在 `application.yml` 中配置：
```yaml
server:
  port: 8080  # 修改为你想要的端口
```

## 📚 API 端点

### FastAPI

#### WebSocket 端点
```
ws://localhost:8000/ai/ws/chat
```

消息格式：
```json
// 发送
{
  "message": "你的问题"
}

// 接收
{
  "type": "start|token|end|error",
  "content": "回复内容"
}
```

#### HTTP 端点（原有功能保留）
```
POST http://localhost:8000/ai/chat
Content-Type: application/json

{
  "query": "你的问题"
}
```

### SpringBoot

```
GET  http://localhost:8080/ai/          -> 重定向到聊天页面
GET  http://localhost:8080/ai/chat-page -> 重定向到聊天页面
GET  http://localhost:8080/chat.html    -> 直接访问聊天页面
```

## 🐛 故障排查

### 1. WebSocket 连接失败
- 检查 FastAPI 是否运行在 `localhost:8000`
- 检查防火墙是否阻止了 WebSocket 连接
- 查看浏览器控制台的错误信息

### 2. 页面加载失败
- 确认 SpringBoot 服务已启动
- 检查 `static/chat.html` 文件是否存在
- 清除浏览器缓存

### 3. 向量搜索失败
- 确认 Milvus 服务运行正常
- 检查是否已上传文档到 Milvus
- 查看 FastAPI 控制台的错误日志

### 4. 流式响应不工作
- 检查 LangChain agent 是否支持 `astream` 方法
- 查看 FastAPI 控制台是否有错误
- 如果 `astream` 不可用，代码会自动回退到模拟流式输出

## 📝 代码文件清单

### 新增/修改的文件

1. **FastAPI 部分**
   - `python-ai-service/api/chat.py` - 添加 WebSocket 端点
   - `python-ai-service/service/rag_service.py` - 添加流式响应函数
   - `python-ai-service/main.py` - 添加 CORS 配置

2. **SpringBoot 部分**
   - `java-service/src/main/java/org/springblade/modules/ai/controller/ChatViewController.java` - 新增页面控制器
   - `java-service/src/main/resources/static/chat.html` - 聊天界面

## 🎯 下一步优化建议

1. **用户认证** - 添加登录功能，保护聊天接口
2. **对话历史** - 保存和加载历史对话
3. **文件上传** - 直接在界面上传文档
4. **多模型切换** - 支持选择不同的 AI 模型
5. **分享对话** - 生成对话链接分享
6. **导出功能** - 导出对话为 PDF/Markdown

## 📞 技术支持

如有问题，请检查：
- FastAPI 控制台日志
- SpringBoot 控制台日志
- 浏览器开发者工具的 Console 和 Network 标签

---

## 🎉 完成！

现在您可以访问 `http://localhost:8080/ai/` 开始使用 AI 知识助手了！
