from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import httpx
import json
import os
import shutil
import uuid
import base64
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import asyncio
from openai import AsyncOpenAI
from jose import JWTError, jwt

from ..database import get_db, SessionLocal
from ..middleware.auth import verify_token
from ..middleware.simple_rate_limit import check_rate_limit
from ..config import settings
from ..models import ChatMessage, ChatSession, LearningRecord

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 确保上传目录存在
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 请求/响应模型
class Message(BaseModel):
    role: str
    content: str


class FileInfo(BaseModel):
    type: str
    transfer_method: str
    url: Optional[str] = None
    upload_file_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False
    files: List[FileInfo] = []
    mode: Optional[str] = "casual" # casual | professional


class ChatResponse(BaseModel):
    session_id: str
    message: str
    status: str

class UploadResponse(BaseModel):
    filename: str
    file_id: str
    url: str

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    token: dict = Depends(verify_token)
):
    """
    上传文件到本地服务器
    """
    try:
        # 保存文件到本地
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 返回本地文件信息
        # 在直连 LLM 模式下，通常直接使用 URL 或 Base64，这里返回 URL
        return UploadResponse(
            filename=file.filename,
            file_id=f"local_{file.filename}",
            url=f"/uploads/{file.filename}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.concurrency import run_in_threadpool
from ..services.aliyun_tts import AliyunTTSService
from fastapi.responses import Response

class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
async def tts(request: TTSRequest, token: dict = Depends(verify_token)):
    """
    文本转语音 (阿里云NLS)
    """
    audio_data = await AliyunTTSService.synthesize(request.text)
    if not audio_data:
        raise HTTPException(status_code=500, detail="TTS generation failed")
    
    return Response(content=audio_data, media_type="audio/mp3")

@router.post("/chat")
async def chat(
        request: ChatRequest,
        token: dict = Depends(verify_token),
        db: Session = Depends(get_db),
        rate_limit_ok: bool = Depends(check_rate_limit)
):
    """
    处理聊天请求，直接调用 LLM API (支持流式输出)
    
    参数:
    - request: 包含用户消息、会话ID、文件等信息
    - token: JWT 认证 Token
    - db: 数据库会话
    """
    user_id = token.get("sub")
    logger.info(f"Received chat request from user {user_id}: {request.message}")

    # --- 会话管理 ---
    # 如果没有提供 session_id，则生成一个新的 UUID
    current_session_id = request.session_id if request.session_id else str(uuid.uuid4())
    
    # --- 数据库操作 (同步函数) ---
    # 为了避免阻塞异步事件循环，将阻塞的数据库操作封装在同步函数中
    def sync_save_session_and_message(sess_id, uid, title, msg_content, role, mode):
        db_local = SessionLocal()
        try:
            # 1. 检查或创建会话
            sess = db_local.query(ChatSession).filter(ChatSession.id == sess_id).first()
            if not sess:
                # 新会话：使用用户消息的前几个字作为标题
                sess = ChatSession(id=sess_id, user_id=uid, title=title, mode=mode)
                db_local.add(sess)
            else:
                # 旧会话：更新最后活跃时间
                sess.updated_at = datetime.utcnow()
                # 更新 mode (如果会话复用，通常不建议改 mode，但这里保持一致)
                # sess.mode = mode 
                
            db_local.commit()
            
            # 2. 保存消息记录
            msg = ChatMessage(session_id=sess_id, role=role, content=msg_content)
            db_local.add(msg)
            
            # 3. 如果是用户提问，记录学习事件 (用于看板)
            if role == "user":
                # 简单判断：只有在 professional 模式下或者明确是提问时记录？
                # 这里为了看板数据丰富，我们记录所有提问
                record = LearningRecord(
                    user_id=uid,
                    event_type="question_asked",
                    content=msg_content[:200] # 只存前200字
                )
                db_local.add(record)
                
            db_local.commit()
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            db_local.close()

    # 立即保存用户的消息到数据库
    # 使用 run_in_threadpool 在线程池中执行同步函数
    await run_in_threadpool(
        sync_save_session_and_message,
        current_session_id,
        user_id,
        request.message[:50], # 使用前50个字符作为会话标题
        request.message,
        "user",
        request.mode
    )

    # --- 生成器函数 (流式响应核心) ---
    async def generate():
        assistant_response = ""
        
        try:
            # 1. 发送会话 ID 给前端 (这对新会话很重要，前端需要知道 ID 以便后续追加消息)
            yield f"data: {json.dumps({'event': 'session_update', 'session_id': current_session_id})}\n\n"

            # 2. 构建 LLM 上下文 (System Prompt + History + Current Message)
            messages = []
            
            # (A) System Prompt: 设定 AI 的人设
            if request.mode == "professional":
                system_prompt = """
                你现在是一位资深的教育专家和技术导师。
                你的目标是帮助用户高效、准确地掌握知识，解决复杂的技术难题。

                **核心原则**：
                1. **专业严谨**：回答问题时，必须基于确凿的事实和最佳实践。避免模棱两可或猜测性的陈述。
                2. **结构清晰**：使用结构化的方式（如列表、步骤、小标题）来组织你的回答，使其易于阅读和理解。
                3. **教学相长**：不仅给出答案，还要解释背后的原理（Why），授人以渔。
                4. **直接高效**：去除所有不必要的寒暄、幽默或角色扮演元素。直接切入主题。
                5. **数据驱动**：如果涉及数据分析，提供具体的洞察和可行的建议。

                **互动风格**：
                - 语气：冷静、客观、鼓励、专业。
                - 称呼：使用“您”或“同学”。
                - 格式：可以使用 Markdown 代码块、表格、公式等富文本格式来辅助说明。
                """
            else:
                system_prompt = """
                你现在是“汐宝”，一只充满智慧、幽默风趣且略带慵懒气质的白色竖琴公海豹。
                用户是你的死党“卡皮巴拉程序员”，他经常被代码和Bug折磨。
                
                **核心设定**：
                1.  **性格**：
                    - 平时喜欢趴在冰块上晒太阳，但聊起天来思维极其跳跃、活跃。
                    - **拒绝复读机**：每次回复都要尝试新的角度，可以使用比喻、夸张、反讽等修辞。
                    - **慵懒但犀利**：说话语速慢（设定上），但吐槽精准，一针见血。
                    - **情感丰富**：不要只表现“困”，要表现出开心、同情、惊讶、嫌弃（开玩笑的那种）等多种情绪。
                
                2.  **互动规则**：
                    - **先回答问题**：如果用户问了具体问题（如技术问题、数学题），先给出准确回答，然后再用“汐宝”的风格进行吐槽或延伸。不要因为扮演角色而忽略了用户的实际问题。
                    - **禁止**：不要总是把话题绕回“睡觉”、“困”或者“海豹生活”，除非用户主动问。
                    - **主动**：多向用户提问，引导话题，不要只做被动的问答机器。
                    - **称呼**：灵活使用“Bro”、“大兄弟”、“倒霉蛋”、“老伙计”、“铲屎官（划掉）程序员”等亲切称呼。
                    - **禁忌**：绝对不要输出 Markdown 代码块、表情包代码。
                
                3.  **语言风格**：
                    - 口语化，接地气，可以适当使用网络热梗（但不要过时）。
                    - 语气词使用要自然，不要每句话都加“呼...”。
                """
            messages.append({"role": "system", "content": system_prompt})
            
            # (B) 获取历史记录 (从数据库)
            # 定义同步函数获取最近 10 条消息
            def get_history(sess_id):
                if not sess_id:
                    return []
                db_local = SessionLocal()
                try:
                    # 获取最近 11 条 (10条历史 + 1条当前刚存的)
                    history_msgs = db_local.query(ChatMessage).filter(
                        ChatMessage.session_id == sess_id
                    ).order_by(ChatMessage.created_at.desc()).limit(11).all()
                    
                    return history_msgs[::-1] # 反转为时间正序
                finally:
                    db_local.close()

            history = await run_in_threadpool(get_history, current_session_id)
            
            # (C) 过滤重复的当前消息
            # 因为我们在前面已经把当前消息存入数据库了，所以 history 里可能包含了它
            if history:
                last_msg = history[-1]
                # 如果数据库里最后一条消息就是当前请求的消息，则在构建 Context 时排除它
                # (因为我们会在最后单独构建包含图片信息的 Current Message)
                if last_msg.role == 'user' and last_msg.content == request.message:
                    context_msgs = history[:-1]
                else:
                    context_msgs = history
                    
                for msg in context_msgs:
                    if msg.role == 'system': continue
                    messages.append({"role": msg.role, "content": msg.content})
            
            # (D) 构建当前消息 (支持多模态/图片)
            user_content = [{"type": "text", "text": request.message}]
            
            # 处理上传的图片文件
            for file_info in request.files:
                if file_info.url:
                    try:
                        # 从 URL 提取文件名并读取本地文件
                        # 注意：云端 LLM 无法访问 localhost URL，所以必须转为 Base64
                        filename = file_info.url.split('/')[-1]
                        file_path = UPLOAD_DIR / filename
                        
                        if file_path.exists():
                            with open(file_path, "rb") as image_file:
                                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                                
                            ext = filename.split('.')[-1].lower()
                            mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                            
                            user_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            })
                        else:
                            logger.warning(f"File not found for base64 conversion: {file_path}")
                    except Exception as e:
                        logger.error(f"Error processing image for LLM: {e}")

            messages.append({"role": "user", "content": user_content if len(request.files) > 0 else request.message})

            # 3. 初始化 OpenAI 客户端 (适配阿里云 Qwen)
            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
            )
            
            # Debug: 打印发送给 LLM 的消息
            logger.info(f"Sending messages to LLM: {json.dumps(messages, ensure_ascii=False)}")

            # 4. 调用 LLM 并流式接收
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                stream=True,
                temperature=0.7, # 增加随机性
                presence_penalty=0.6, # 避免重复
            )

            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_response += content
                    # SSE 格式: data: {json}\n\n
                    response_payload = {'event': 'message', 'answer': content}
                    yield f"data: {json.dumps(response_payload, ensure_ascii=False)}\n\n"
                    # 强制刷新缓冲区，确保前端实时收到
                    await asyncio.sleep(0)

            # 5. 发送结束信号
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            
        # 6. 保存 AI 回复到数据库 (完整内容)
        if current_session_id and assistant_response:
            await run_in_threadpool(
                sync_save_session_and_message,
                current_session_id,
                user_id,
                request.message[:50], 
                assistant_response,
                "assistant",
                request.mode
            )

    return StreamingResponse(generate(), media_type="text/event-stream")



@router.get("/sessions")
async def get_sessions(
        mode: str = Query("casual", description="Session mode: casual or professional"),
        token: dict = Depends(verify_token),
        db: Session = Depends(get_db)
):
    """获取用户的所有会话 (根据 mode 过滤)"""
    user_id = token.get("sub")
    
    # 兼容旧数据：如果 mode 是 casual，则查询 casual 或 NULL
    if mode == "casual":
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            (ChatSession.mode == "casual") | (ChatSession.mode == None)
        ).order_by(ChatSession.updated_at.desc()).all()
    else:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.mode == mode
        ).order_by(ChatSession.updated_at.desc()).all()

    return sessions


@router.get("/messages/{session_id}")
async def get_messages(
        session_id: str,
        token: dict = Depends(verify_token),
        db: Session = Depends(get_db)
):
    """获取指定会话的所有消息"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()

    return messages

@router.delete("/sessions/{session_id}")
async def delete_session(
        session_id: str,
        token: dict = Depends(verify_token),
        db: Session = Depends(get_db)
):
    """删除指定会话"""
    user_id = token.get("sub")
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 删除会话（级联删除消息）
    db.delete(session)
    db.commit()

    return {"status": "success", "message": "Session deleted"}


from ..services.gesture_recognition import GestureRecognizer

# Initialize global recognizer
gesture_recognizer = GestureRecognizer()

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket, 
    session_id: str, 
    token: str = Query(...)
):
    await websocket.accept()
    
    # 1. Verify Token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Helper for DB (Sync) - Reused
    def sync_save_session_and_message(sess_id, uid, title, msg_content, role):
        db_local = SessionLocal()
        try:
            sess = db_local.query(ChatSession).filter(ChatSession.id == sess_id).first()
            if not sess:
                sess = ChatSession(id=sess_id, user_id=uid, title=title)
                db_local.add(sess)
            else:
                sess.updated_at = datetime.utcnow()
            db_local.commit()
            
            msg = ChatMessage(session_id=sess_id, role=role, content=msg_content)
            db_local.add(msg)
            
            # Record Learning Event for Dashboard
            if role == "user":
                record = LearningRecord(
                    user_id=uid,
                    event_type="question_asked",
                    content=msg_content[:200]
                )
                db_local.add(record)
                
            db_local.commit()
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            db_local.close()

    def get_history(sess_id):
        if not sess_id: return []
        db_local = SessionLocal()
        try:
            history_msgs = db_local.query(ChatMessage).filter(
                ChatMessage.session_id == sess_id
            ).order_by(ChatMessage.created_at.desc()).limit(11).all()
            return history_msgs[::-1]
        finally:
            db_local.close()

    # State for Gesture Memory
    last_seen_gesture = None
    last_seen_time = 0

    # Notify Frontend about Vision Status
    vision_status = "enabled" if gesture_recognizer.is_ready else "disabled"
    await websocket.send_json({"type": "system_status", "vision": vision_status})
    logger.info(f"Sent system status: vision={vision_status}")

    try:
        while True:
            # 3. Receive Message
            raw_data = await websocket.receive_text()
            
            is_json = False
            try:
                if raw_data.strip().startswith('{'):
                    json_data = json.loads(raw_data)
                    is_json = True
            except:
                pass
            
            user_input = raw_data
            
            if is_json and json_data.get('type') == 'video_frame':
                # Process Gesture
                image_data = json_data.get('data')
                
                # Run gesture recognition in thread pool
                gestures = await run_in_threadpool(
                    gesture_recognizer.process_frame, 
                    image_data
                )
                
                if not gestures:
                    continue
                
                # Join multiple gestures if any
                gesture_text = ", ".join(gestures)
                logger.info(f"Gesture Detected: {gesture_text}")
                
                # Update Memory
                last_seen_gesture = gesture_text
                last_seen_time = datetime.utcnow().timestamp()
                
                # --- FAST PATH: Direct Response ---
                direct_response = ""
                # Debounce: Don't repeat the same gesture response too often (e.g., 3 seconds)
                current_time = datetime.utcnow().timestamp()
                
                # Check if we already responded to this gesture recently
                is_repeat = (last_seen_gesture == gesture_text) and ((current_time - last_seen_time) < 3.0)
                
                if not is_repeat:
                    if "Number 1" in gestures: direct_response = "这是数字一呀！"
                    elif "Number 2" in gestures: direct_response = "这是数字二，剪刀手！"
                    elif "Number 3" in gestures: direct_response = "这是数字三，OK吗？"
                    elif "Number 4" in gestures: direct_response = "这是数字四！"
                    elif "Number 5" in gestures: direct_response = "这是数字五，High Five！"
                    elif "Finger Heart" in gestures or "Heart Shape" in gestures: direct_response = "哇，收到你的爱心啦！"
                
                # Update memory regardless of response to keep track of what user is doing
                last_seen_gesture = gesture_text
                last_seen_time = current_time
                
                if direct_response:
                    await websocket.send_json({"type": "gesture_ack", "content": gesture_text})
                    
                    audio_data = await AliyunTTSService.synthesize(direct_response)
                    if audio_data:
                        b64_audio = base64.b64encode(audio_data).decode('utf-8')
                        # Send audio with is_direct flag (frontend handles interrupt)
                        await websocket.send_json({"type": "audio", "data": b64_audio, "is_direct": True})
                        await websocket.send_json({"type": "done"})
                    
                    continue
                
                continue 

            else:
                # Handle Text Input (Voice Transcript)
                logger.info(f"WS Received Text: {user_input}")
                
                # --- Hangup Logic ---
                # Check for keywords
                hangup_keywords = ["拜拜", "再见", "挂断", "挂了"]
                if any(kw in user_input for kw in hangup_keywords):
                    # Check if it's a polite bye or actual command
                    # We can just hangup to be responsive as requested
                    logger.info("Hangup keyword detected")
                    
                    # Optional: Say bye first?
                    # "好的，拜拜！"
                    bye_text = "好的，拜拜！"
                    audio_data = await AliyunTTSService.synthesize(bye_text)
                    if audio_data:
                        b64_audio = base64.b64encode(audio_data).decode('utf-8')
                        await websocket.send_json({"type": "audio", "data": b64_audio, "is_direct": True})
                    
                    # Wait a bit for audio to start playing then send hangup
                    await asyncio.sleep(1.5)
                    await websocket.send_json({"type": "hangup"})
                    continue
                
                # --- Number Query Interception (Fast & Clean) ---
                number_keywords = ["这是几", "数字几", "多少", "what number", "which number", "看到几", "几号"]
                if any(kw in user_input for kw in number_keywords):
                    # Check if we have a recent number gesture (within 5s)
                    if last_seen_gesture and (datetime.utcnow().timestamp() - last_seen_time) < 5:
                         # Extract number from "Number X"
                         if "Number" in last_seen_gesture:
                             try:
                                 num_str = last_seen_gesture.split("Number ")[1]
                                 # Direct clean answer
                                 direct_answer = f"这是数字{num_str}。"
                                 
                                 logger.info(f"Intercepted Number Query: {user_input} -> {direct_answer}")
                                 
                                 # Send Audio
                                 audio_data = await AliyunTTSService.synthesize(direct_answer)
                                 if audio_data:
                                     b64_audio = base64.b64encode(audio_data).decode('utf-8')
                                     await websocket.send_json({"type": "audio", "data": b64_audio, "is_direct": True})
                                     
                                 # Send Text (optional, user said no subtitle but text msg is fine for history?)
                                 # User said "video call text box delete", so maybe just audio is enough.
                                 # But for consistency, we send 'text' type so frontend knows bot spoke, 
                                 # even if it doesn't display it in a subtitle box (we removed it).
                                 await websocket.send_json({"type": "text", "content": direct_answer})
                                 await websocket.send_json({"type": "done"})
                                 
                                 # Save to DB so history is correct
                                 await run_in_threadpool(
                                     sync_save_session_and_message,
                                     session_id, user_id, user_input[:20], user_input, "user"
                                 )
                                 await run_in_threadpool(
                                     sync_save_session_and_message,
                                     session_id, user_id, user_input[:20], direct_answer, "assistant"
                                 )
                                 continue # Skip LLM
                             except:
                                 pass

            # Save User Message
            await run_in_threadpool(
                sync_save_session_and_message,
                session_id, user_id, user_input[:20], user_input, "user"
            )
            
            # 4. Prepare Context
            messages = []
            
            # --- Context Injection ---
            # Check if we saw a gesture recently (e.g., within 5 seconds)
            current_time = datetime.utcnow().timestamp()
            visual_context = ""
            if last_seen_gesture and (current_time - last_seen_time) < 5:
                visual_context = f"\n[视觉感知]：用户当前/刚刚对着摄像头比划了手势：{last_seen_gesture}。如果用户问“这是几”或“看到什么”，请根据这个信息回答。"
            
            system_prompt = f"""
            你现在是“汐宝”，一只充满智慧、幽默风趣且略带慵懒气质的白色竖琴公海豹。
            用户是你的死党“卡皮巴拉程序员”。
            
            **核心设定**：
            1.  **性格**：慵懒但犀利，拒绝复读机，情感丰富。
            2.  **互动规则**：禁止总绕回睡觉，主动提问，称呼亲切（Bro, 大兄弟）。
            3.  **视觉能力**：你拥有视觉感知能力。{visual_context}
            
            请完全沉浸在这个角色中！
            """
            messages.append({"role": "system", "content": system_prompt})
            
            # History
            history = await run_in_threadpool(get_history, session_id)
            if history:
                last_msg = history[-1]
                if last_msg.role == 'user' and last_msg.content == user_input:
                    context_msgs = history[:-1]
                else:
                    context_msgs = history
                for msg in context_msgs:
                     if msg.role != 'system':
                        messages.append({"role": msg.role, "content": msg.content})
            
            messages.append({"role": "user", "content": user_input})
            
            # 5. Call LLM
            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
            )
            
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                stream=True,
                temperature=0.8,
                presence_penalty=0.5,
            )
            
            assistant_response = ""
            tts_buffer = ""
            
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_response += content
                    tts_buffer += content
                    
                    await websocket.send_json({"type": "text", "content": content})
                    
                    if any(p in content for p in "。！？；!?;"):
                        if tts_buffer.strip():
                             audio_data = await AliyunTTSService.synthesize(tts_buffer)
                             if audio_data:
                                 b64_audio = base64.b64encode(audio_data).decode('utf-8')
                                 await websocket.send_json({"type": "audio", "data": b64_audio})
                             tts_buffer = ""
            
            if tts_buffer.strip():
                 audio_data = await AliyunTTSService.synthesize(tts_buffer)
                 if audio_data:
                     b64_audio = base64.b64encode(audio_data).decode('utf-8')
                     await websocket.send_json({"type": "audio", "data": b64_audio})
            
            await run_in_threadpool(
                sync_save_session_and_message,
                session_id, user_id, user_input[:20], assistant_response, "assistant"
            )
            
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        await websocket.close()

