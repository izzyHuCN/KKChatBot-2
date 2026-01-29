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
from ..models import ChatMessage, ChatSession

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
    """
    user_id = token.get("sub")
    logger.info(f"Received chat request from user {user_id}: {request.message}")

    # Determine initial session_id or generate new one
    current_session_id = request.session_id if request.session_id else str(uuid.uuid4())
    
    # Define sync DB operations
    def sync_save_session_and_message(sess_id, uid, title, msg_content, role):
        db_local = SessionLocal()
        try:
            # Check/Create Session
            sess = db_local.query(ChatSession).filter(ChatSession.id == sess_id).first()
            if not sess:
                sess = ChatSession(id=sess_id, user_id=uid, title=title)
                db_local.add(sess)
            else:
                # Update timestamp
                sess.updated_at = datetime.utcnow()
                # Update title if it's the first message and title is default
                # (Optional, but good for UX if we want to summarize later)
                
            db_local.commit()
            
            # Save Message
            msg = ChatMessage(session_id=sess_id, role=role, content=msg_content)
            db_local.add(msg)
            db_local.commit()
        except Exception as e:
            logger.error(f"DB Error: {e}")
        finally:
            db_local.close()

    # Save User Message immediately
    await run_in_threadpool(
        sync_save_session_and_message,
        current_session_id,
        user_id,
        request.message[:50],
        request.message,
        "user"
    )

    async def generate():
        assistant_response = ""
        
        try:
            # Notify frontend of the session ID (especially if it's new)
            yield f"data: {json.dumps({'event': 'session_update', 'session_id': current_session_id})}\n\n"

            # Prepare messages for LLM
            messages = []
            
            # --- System Prompt (Xibao Persona) ---
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
                - **禁止**：不要总是把话题绕回“睡觉”、“困”或者“海豹生活”，除非用户主动问。
                - **主动**：多向用户提问，引导话题，不要只做被动的问答机器。
                - **称呼**：灵活使用“Bro”、“大兄弟”、“倒霉蛋”、“老伙计”、“铲屎官（划掉）程序员”等亲切称呼。
                - **禁忌**：绝对不要输出 Markdown 代码块、表情包代码。
            
            3.  **语言风格**：
                - 口语化，接地气，可以适当使用网络热梗（但不要过时）。
                - 语气词使用要自然，不要每句话都加“呼...”。
            
            请完全沉浸在这个角色中，大胆发挥你的想象力，给你的朋友带来快乐和启发！
            """
            messages.append({"role": "system", "content": system_prompt})
            
            # --- Fetch History Context ---
            # Fetch last 10 messages from DB for context
            # Exclude the current user message which was just saved (or simply query before saving, but we saved it async)
            # Actually, sync_save_session_and_message saves it, so it IS in DB.
            # We want to retrieve previous messages.
            
            # Use run_in_threadpool for blocking DB operations
            def get_history(sess_id):
                if not sess_id:
                    return []
                db_local = SessionLocal()
                try:
                    # Get last 11 messages (10 history + 1 current)
                    # We order by created_at DESC to get latest first, then reverse
                    history_msgs = db_local.query(ChatMessage).filter(
                        ChatMessage.session_id == sess_id
                    ).order_by(ChatMessage.created_at.desc()).limit(11).all()
                    
                    return history_msgs[::-1] # Reverse to chronological order
                finally:
                    db_local.close()

            history = await run_in_threadpool(get_history, current_session_id)
            
            # Filter out the last message if it is the same as the current request (to avoid duplication if logic overlaps)
            # But simpler: just append history BEFORE the current message construction
            # Wait, `history` contains the current message because we saved it at line 143.
            # So we should exclude the last one from `history` if it matches the current role/content,
            # OR just use the history as the source of truth?
            # Problem: `history` from DB doesn't have the image/file info formatted for LLM yet (it just has text).
            # The current `request.message` is processed into `user_content` which supports images.
            # So we should use `history[:-1]` (all except the last one) as context, 
            # and use `user_content` for the final message.
            
            if history:
                # If the last message in history is the user's current message, exclude it
                # We can check by role and content roughly, or just assume the last one is ours since we just saved it.
                # Ideally, we check if history[-1].role == 'user' and history[-1].content == request.message
                
                last_msg = history[-1]
                if last_msg.role == 'user' and last_msg.content == request.message:
                    context_msgs = history[:-1]
                else:
                    context_msgs = history
                    
                for msg in context_msgs:
                    # Skip system messages if any (shouldn't be in DB usually, but just in case)
                    if msg.role == 'system':
                        continue
                    messages.append({"role": msg.role, "content": msg.content})
            
            # Construct current message content
            user_content = [{"type": "text", "text": request.message}]
            
            # Handle files (assuming they are images)
            for file_info in request.files:
                if file_info.url:
                    # Construct full URL if relative
                    # Fix: Localhost URLs are not accessible by cloud LLMs. 
                    # We must convert local image files to Base64 data URIs.
                    try:
                        # Extract filename from URL (assuming /uploads/filename format)
                        filename = file_info.url.split('/')[-1]
                        file_path = UPLOAD_DIR / filename
                        
                        if file_path.exists():
                            with open(file_path, "rb") as image_file:
                                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                                
                            # Determine mime type based on extension
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

            # Initialize OpenAI Client
            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
            )

            # Call LLM
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                stream=True
            )

            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_response += content
                    response_payload = {'event': 'message', 'answer': content}
                    yield f"data: {json.dumps(response_payload, ensure_ascii=False)}\n\n"
                    # Force flush
                    await asyncio.sleep(0)

            # Send done signal
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            
        # Save Assistant Message to DB
        if current_session_id and assistant_response:
            await run_in_threadpool(
                sync_save_session_and_message,
                current_session_id,
                user_id,
                request.message[:50], 
                assistant_response,
                "assistant"
            )

    return StreamingResponse(generate(), media_type="text/event-stream")



@router.get("/sessions")
async def get_sessions(
        token: dict = Depends(verify_token),
        db: Session = Depends(get_db)
):
    """获取用户的所有会话"""
    user_id = token.get("sub")
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == user_id
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

    try:
        while True:
            # 3. Receive Message
            data = await websocket.receive_text()
            logger.info(f"WS Received: {data}")
            
            # Save User Message
            await run_in_threadpool(
                sync_save_session_and_message,
                session_id, user_id, data[:20], data, "user"
            )
            
            # 4. Prepare Context
            messages = []
            
            # --- System Prompt (Xibao Persona) ---
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
                - **禁止**：不要总是把话题绕回“睡觉”、“困”或者“海豹生活”，除非用户主动问。
                - **主动**：多向用户提问，引导话题，不要只做被动的问答机器。
                - **称呼**：灵活使用“Bro”、“大兄弟”、“倒霉蛋”、“老伙计”、“铲屎官（划掉）程序员”等亲切称呼。
                - **禁忌**：绝对不要输出 Markdown 代码块、表情包代码。
            
            3.  **语言风格**：
                - 口语化，接地气，可以适当使用网络热梗（但不要过时）。
                - 语气词使用要自然，不要每句话都加“呼...”。
            
            请完全沉浸在这个角色中，大胆发挥你的想象力，给你的朋友带来快乐和启发！
            """
            messages.append({"role": "system", "content": system_prompt})
            
            # History
            history = await run_in_threadpool(get_history, session_id)
            if history:
                # Exclude last if duplicate (similar logic to chat endpoint)
                last_msg = history[-1]
                if last_msg.role == 'user' and last_msg.content == data:
                    context_msgs = history[:-1]
                else:
                    context_msgs = history
                for msg in context_msgs:
                     if msg.role != 'system':
                        messages.append({"role": msg.role, "content": msg.content})
            
            messages.append({"role": "user", "content": data})
            
            # 5. Call LLM
            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
            )
            
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                stream=True,
                temperature=0.8, # 增加随机性，避免回复单一
                presence_penalty=0.5, # 鼓励讨论新话题
                frequency_penalty=0.5 # 减少重复
            )
            
            assistant_response = ""
            tts_buffer = ""
            
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_response += content
                    tts_buffer += content
                    
                    # Send Text Chunk
                    await websocket.send_json({"type": "text", "content": content})
                    
                    # Check for sentence end for TTS
                    # Simple check: punctuation
                    if any(p in content for p in "。！？；!?;"):
                        # Synthesize TTS
                        if tts_buffer.strip():
                             audio_data = await AliyunTTSService.synthesize(tts_buffer)
                             if audio_data:
                                 # Send Audio Chunk (Base64)
                                 b64_audio = base64.b64encode(audio_data).decode('utf-8')
                                 await websocket.send_json({"type": "audio", "data": b64_audio})
                             tts_buffer = ""
            
            # Flush remaining TTS
            if tts_buffer.strip():
                 audio_data = await AliyunTTSService.synthesize(tts_buffer)
                 if audio_data:
                     b64_audio = base64.b64encode(audio_data).decode('utf-8')
                     await websocket.send_json({"type": "audio", "data": b64_audio})
            
            # Save Assistant Message
            await run_in_threadpool(
                sync_save_session_and_message,
                session_id, user_id, data[:20], assistant_response, "assistant"
            )
            
            # Send Done
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        await websocket.close()

