# KKChatBot-2 项目技术文档

## 1. 项目概述

KKChatBot-2 是一个基于 Vue 3 (前端) 和 FastAPI (后端) 构建的现代化 AI 聊天助手。它集成了**实时视频通话**、**手势识别**、**多模态交互**（文本/图片/视觉）、流式响应以及数字人视频状态反馈等高级功能。

**核心亮点**：
*   **实时视频通话**: 真正的 WebRTC 视频流传输，支持与 AI 数字人面对面交流。
*   **视觉感知 (Computer Vision)**: 集成 `MediaPipe`，能实时识别用户手势（如数字计数、比心）。
*   **极速响应 (Fast Path)**: 针对特定手势（如数字），后端直接拦截并毫秒级响应，无需等待大模型。
*   **多模态融合**: 视觉记忆与语言模型结合，支持“这是几？”等需要视觉上下文的自然问答。
*   **智能打断与挂断**: 支持语音/手势随时打断 AI 发言，支持“拜拜”语音自动挂断。

## 2. 系统架构

### 2.1 技术栈
*   **前端**: Vue 3, Vite, Axios, WebSocket (原生), CSS3 Animations
*   **后端**: Python 3.9 (Full Image), FastAPI, Uvicorn, SQLAlchemy (SQLite), Redis (可选)
*   **AI 服务**: 阿里云通义千问 (Qwen-VL-Max) 用于 LLM, 阿里云 NLS 用于 TTS (语音合成)
*   **计算机视觉**: `MediaPipe Hands` (Google), `OpenCV` (Headless)
*   **部署**: Docker, Docker Compose

### 2.2 核心流程图

#### 系统架构概览
```mermaid
graph TD
    User[用户] -->|语音/视频流| Frontend[前端 Vue 3]
    
    subgraph Frontend_App [前端应用]
        UI[界面组件 ChatView]
        WS_Client[WebSocket 客户端]
        Camera[摄像头流处理]
        Gesture_UI[视觉状态/字幕]
    end
    
    Frontend -->|REST / SSE| Backend_API[后端 API]
    Frontend -->|WebSocket JSON or Binary| Backend_WS[后端 WebSocket]
    
    subgraph Backend_App [后端 FastAPI]
        Router[路由层]
        CV_Worker[手势识别线程池]
        Fast_Path[极速响应拦截器]
        Chat_Service[聊天业务逻辑]
        TTS_Service[阿里云 TTS 服务]
    end
    
    Backend_WS --> CV_Worker
    CV_Worker -->|手势结果| Fast_Path
    Fast_Path -->|直接回复| TTS_Service
    Fast_Path -->|视觉记忆| Chat_Service
    Chat_Service -->|流式对话| LLM[阿里云 Qwen-VL]
    Chat_Service -->|语音合成| TTS[阿里云 NLS]
```

#### 实时视频与手势交互流程 (核心)
这个流程图展示了用户视频通话时，视觉与语音的双链路处理机制。

```mermaid
sequenceDiagram
    participant U as User (用户)
    participant F as Frontend (ChatView)
    participant W as WebSocket (chat.py)
    participant CV as GestureRecognizer (MediaPipe)
    participant L as LLM (Qwen-VL)

    Note over U, F: 开启视频通话
    F->>W: 建立连接 (WS)
    W-->>F: 发送系统状态 (Vision Enabled)
    
    par 视频流链路
        loop 每 200ms
            F->>W: 发送视频帧 (Base64)
            W->>CV: 识别手势
            CV-->>W: 返回结果 (如 "Number 5")
            
            alt 极速响应 (Fast Path)
                W->>W: 检测到新数字手势
                W-->>F: 发送语音 "这是数字五！" (打断当前对话)
            else 视觉记忆
                W->>W: 更新 last_seen_gesture = "Number 5"
            end
        end
    and 语音链路
        U->>F: 说话 "这是几？"
        F->>W: 发送文本 "这是几？"
        
        alt 命中视觉拦截
            W->>W: 检查 5秒内视觉记忆
            W->>W: 发现 "Number 5"
            W-->>F: 直接回复 "这是数字五。" (跳过 LLM)
        else 普通对话
            W->>L: 发送文本 + 视觉上下文
            L-->>W: 生成回复
            W-->>F: 发送语音流
        end
    end
    
    Note over U, F: 挂断机制
    U->>F: 说话 "拜拜"
    F->>W: 发送文本
    W->>W: 关键词检测
    W-->>F: 回复 "拜拜！" 并发送 Hangup 指令
    F->>F: 关闭摄像头与连接
```

## 3. 核心模块详解

### 3.1 后端 (Backend)

*   **手势识别 (`backend/app/services/gesture_recognition.py`)**:
    *   **鲁棒算法**: 
        *   使用几何特征（指尖与指关节距离比）而非简单的坐标阈值，支持任意角度的手势识别。
        *   **大拇指修正**: 引入指尖到小指根部的距离判断，彻底解决了“多算一根手指”的常见误判问题。
    *   **依赖管理**: 锁定 `mediapipe==0.10.9` 和 `protobuf==3.20.3`，确保在 Docker 环境下的稳定性。
    *   **线程池**: 所有的 CV 处理都在 `run_in_threadpool` 中执行，保证 WebSocket 主线程不阻塞。

*   **聊天逻辑 (`backend/app/api/chat.py`)**:
    *   **Fast Path Interception**: 在调用 LLM 之前，先检查是否命中“数字查询”或“挂断”意图，命中则直接返回，显著降低延迟。
    *   **视觉记忆 (Visual Memory)**: 缓存最近一次识别到的手势及其时间戳（有效期 5 秒），用于辅助回答“这是什么”等代词问题。
    *   **防抖动 (Debounce)**: 对连续相同的手势响应设置 3 秒冷却时间，防止 AI 变身复读机。

### 3.2 前端 (Frontend)

*   **视频通话视图 (`frontend/src/views/ChatView.vue`)**:
    *   **视觉状态指示器**: 右上角红/绿点实时显示后端视觉引擎是否就绪。
    *   **双视频流 UI**: 支持主画面与画中画 (PIP) 切换，默认 AI 为主画面。
    *   **状态机**: 
        *   `Sleeping` (常态): 汐宝睡觉。
        *   `Thinking` (视频中默认): 汐宝倾听/思考。
        *   `Talking` (回答中): 汐宝说话。
    *   **无感传输**: 视频帧经过压缩后通过 WebSocket 传输，保证低带宽下的流畅度。

## 4. 功能使用指南

### 4.1 开启视频通话
1.  点击聊天框右侧的 **📹 摄像头图标**。
2.  等待连接成功（右上角出现绿色“视觉已开启”提示）。
3.  此时你可以看到汐宝醒来并开始倾听。

### 4.2 手势互动
*   **数字识别**: 伸出 1-5 根手指（任意角度），汐宝会立即识别并语音播报（如“这是数字二，剪刀手！”）。
*   **特殊手势**: 比个“爱心”或“比心”，汐宝会有惊喜反应。
*   **组合问答**: 一边比划一边问“这是几？”，汐宝会根据看到的画面回答。

### 4.3 语音控制
*   **打断**: 汐宝说话时，你只需开口说话或做新手势，它会立即停止当前发言并回应你。
*   **挂断**: 对着麦克风说“拜拜”、“再见”或“挂断”，系统会自动结束通话。

## 5. 部署与维护

*   **启动命令**:
    *   后端: `docker-compose up -d backend` (推荐使用 Docker 以确保 CV 环境依赖正确)
    *   前端: `npm run dev`
*   **环境变量**: 复制 `.env.example` 到 `.env` 并填入阿里云 Key。
*   **注意事项**: 
    *   MediaPipe 需要 Python 3.9 环境，不要随意升级基础镜像。
    *   如果右上角显示“视觉初始化失败”，请检查后端日志 `docker-compose logs backend`。
