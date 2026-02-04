<template>
  <div class="chat-container">
    <!-- 动态背景 -->
    <div class="ocean-bg">
      <div class="bubble-1"></div>
      <div class="bubble-2"></div>
      <div class="bubble-3"></div>
      <div class="wave"></div>
    </div>
    
    <!-- 视频数字人 (MP4) -->
    <div 
      class="video-avatar-wrapper"
      ref="avatarWrapper"
      :style="{ left: avatarX + 'px', top: avatarY + 'px' }"
      @mousedown="startDrag"
    >
      <div class="water-tank">
        <video 
          ref="avatarVideo"
          :src="mainAvatarSource" 
          autoplay 
          loop 
          muted 
          playsinline
          class="avatar-video"
        ></video>
        <!-- 水缸光效遮罩 -->
        <div class="tank-overlay"></div>
        <div class="tank-highlight"></div>
      </div>
    </div>

    <!-- 侧边栏 -->
    <div class="sidebar" :class="{ open: isSidebarOpen }">
      <div class="sidebar-header">
        <h2>历史会话</h2>
        <button class="new-chat-btn" @click="startNewChat">
          + 新建对话
        </button>
      </div>
      <div class="sidebar-content">
        <div 
          v-for="session in sessions" 
          :key="session.id" 
          class="session-item"
          :class="{ active: session.id === currentSessionId }"
          @click="loadSession(session.id)"
        >
          <span class="session-title">{{ session.title || '新对话' }}</span>
          <span class="session-date">{{ formatDate(session.updated_at) }}</span>
          <button class="delete-session-btn" @click.stop="deleteSession(session.id)">×</button>
        </div>
      </div>
    </div>
    
    <!-- 遮罩层 -->
    <div v-if="isSidebarOpen" class="overlay" @click="isSidebarOpen = false"></div>

    <!-- Background Music -->
    <audio ref="bgmAudio" src="/avatars/xibao_bgm.mp3" loop></audio>

    <div class="chat-header">
      <!-- 侧边栏切换按钮 -->
      <button class="icon-btn sidebar-toggle" @click="toggleSidebar">
        ☰
      </button>

      <div class="header-content">
        <div class="logo-wrapper">
          <img :src="botAvatar" alt="Logo" class="header-logo" @error="(e) => handleAvatarError(e, 'bot')" />
          <div class="status-dot"></div>
        </div>
        <div class="title-wrapper">
          <h1>汐宝 XIBAO</h1>
          <span class="subtitle">KKChatBot-2</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="icon-btn" @click="toggleVoiceOutput" :class="{ active: voiceOutputEnabled }" title="语音播报">
          <span v-if="voiceOutputEnabled">🔊</span>
          <span v-else>🔇</span>
        </button>
      </div>
    </div>
    
    <div class="messages-container" ref="messagesContainer">
      <div v-for="(msg, index) in messages" :key="index" :class="['message-wrapper', msg.role === 'user' ? 'user' : 'assistant']">
        <div class="avatar">
          <img :src="msg.role === 'user' ? userAvatar : botAvatar" alt="avatar" />
        </div>
        <div class="message-content">
          <div class="bubble">
            <p v-if="msg.type !== 'image'">{{ msg.content }}</p>
            <img v-else :src="msg.content" class="uploaded-image" alt="uploaded" />
          </div>
          <span class="timestamp">{{ formatTime(new Date()) }}</span>
        </div>
      </div>
      
      <!-- Loading Indicator -->
      <div v-if="loading" class="message-wrapper assistant">
        <div class="avatar">
          <img :src="botAvatar" alt="avatar" />
        </div>
        <div class="message-content">
          <div class="bubble loading-bubble">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <!-- 附件预览区域 -->
      <div v-if="attachedFiles.length > 0" class="attachments-preview">
        <div v-for="(file, index) in attachedFiles" :key="index" class="attachment-chip">
          <span class="file-name">{{ file.filename }}</span>
          <span class="remove-btn" @click="removeAttachment(index)">×</span>
        </div>
      </div>

      <div class="input-wrapper glass-panel">
        <!-- 文件上传 -->
        <input type="file" ref="fileInput" @change="handleFileUpload" style="display: none" />
        <button class="action-btn" @click="$refs.fileInput.click()" title="上传文件" :disabled="loading">
          📎
        </button>

        <!-- 文本输入 -->
        <input 
          v-model="userInput" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="输入指令..." 
          :disabled="loading"
          class="tech-input"
        />

        <!-- 语音输入 -->
        <button class="action-btn" @click="toggleVoiceInput" :class="{ recording: isRecording }" title="语音输入" :disabled="loading">
          <span v-if="isRecording">🔴</span>
          <span v-else>🎤</span>
        </button>

        <!-- 实时语音通话 -->
        <button class="action-btn" @click="toggleVideoCallMode" :class="{ active: isVideoCallMode }" title="视频通话" :disabled="loading">
          <span v-if="isVideoCallMode">📹</span>
          <span v-else>📹</span>
        </button>

        <button class="send-btn" @click="sendMessage" :disabled="loading || !userInput.trim()">
          SEND
        </button>
      </div>
    </div>
    
    <!-- Video Call Overlay -->
    <div v-if="isVideoCallMode" class="video-call-overlay">
      <div class="video-container">
        <!-- Main Video (Swappable) -->
        <div class="main-video-wrapper">
             <!-- If main is bot -->
             <video 
               v-if="!isUserMain"
               ref="mainBotVideo"
               :src="videoAvatarSource" 
               autoplay loop muted playsinline
               class="main-video"
             ></video>
             
             <!-- If main is user -->
             <video 
               v-else
               ref="mainUserVideo"
               autoplay muted playsinline
               class="main-video user-cam"
             ></video>
             
             <!-- Recognition Result Overlay -->
             <div v-if="lastGesture" class="gesture-toast">
                🖐️ {{ lastGesture }}
             </div>

             <!-- Vision Status Indicator -->
             <div class="vision-status" :class="{ 'active': visionStatus === 'enabled' }">
                <span class="status-dot"></span>
                {{ visionStatus === 'enabled' ? '视觉已开启' : '视觉初始化中/失败' }}
             </div>
        </div>
        
        <!-- Small Video (PIP) -->
        <div class="pip-video-wrapper" @click="isUserMain = !isUserMain">
             <!-- If main is bot, pip is user -->
             <video 
               v-if="!isUserMain"
               ref="pipUserVideo"
               autoplay muted playsinline
               class="pip-video user-cam"
             ></video>
             
             <!-- If main is user, pip is bot -->
             <video 
               v-else
               ref="pipBotVideo"
               :src="videoAvatarSource" 
               autoplay loop muted playsinline
               class="pip-video"
             ></video>
        </div>
        
        <!-- Controls -->
        <div class="video-controls">
            <button class="control-btn" @click="toggleCamera" :class="{ off: !isCameraOn }">
                {{ isCameraOn ? '📷 On' : '📷 Off' }}
            </button>
            <button class="control-btn close-btn" @click="toggleVideoCallMode">
                ❌ 挂断
            </button>
        </div>
      </div>
      
      <!-- Hidden Canvas for Frame Capture -->
      <canvas ref="captureCanvas" style="display:none;"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
// 状态视频路径
const videoPaths = {
  // User requested to simplify: Thinking/Listening -> thinking.mp4, Talking -> talking.mp4
  sleeping: '/avatars/xibao_sleeping.mp4', 
  thinking: '/avatars/xibao_thinking.mp4',
  talking: '/avatars/xibao_talking.mp4'
};

// ... existing code ...

// --- Video Call Mode ---
const isVideoCallMode = ref(false);
const isUserMain = ref(false); // Default: Bot is main
const isCameraOn = ref(true);
const localStream = ref(null);
const mainUserVideo = ref(null);
const pipUserVideo = ref(null);
const captureCanvas = ref(null);
const lastGesture = ref('');
const visionStatus = ref('disabled'); // enabled, disabled
let frameInterval = null;

const toggleVideoCallMode = async () => {
    if (isVideoCallMode.value) {
        stopVideoCall();
    } else {
        await startVideoCall();
    }
};

const startVideoCall = async () => {
    // Start Real-time audio first (reusing existing logic)
    if (!isRealTimeMode.value) {
        // Ensure we enable audio recording for speech recognition
        await startRealTimeMode();
        
        // Wait for WebSocket to be open (up to 5 seconds)
        let retries = 0;
        while ((!websocket || websocket.readyState !== WebSocket.OPEN) && retries < 50) {
             await new Promise(r => setTimeout(r, 100));
             retries++;
        }
        
        if (!websocket || websocket.readyState !== WebSocket.OPEN) {
             alert("无法连接到语音服务器，请稍后再试。");
             stopRealTimeMode();
             return;
        }
    }
    
    isVideoCallMode.value = true;
    isCameraOn.value = true;
    
    await nextTick(); // Wait for DOM
    await startCamera();
    
    // Start sending frames
    startFrameTransmission();
};

const stopVideoCall = () => {
    isVideoCallMode.value = false;
    stopCamera();
    stopFrameTransmission();
    
    // Ensure we stop real-time mode to reset state (as requested by user interaction flow)
    stopRealTimeMode(); 
};

const startCamera = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        localStream.value = stream;
        attachStreamToVideo();
    } catch (e) {
        console.error("Camera error:", e);
        alert("无法访问摄像头");
        isCameraOn.value = false;
    }
};

const stopCamera = () => {
    if (localStream.value) {
        localStream.value.getTracks().forEach(track => track.stop());
        localStream.value = null;
    }
    isCameraOn.value = false;
};

const toggleCamera = async () => {
    if (isCameraOn.value) {
        stopCamera();
    } else {
        isCameraOn.value = true;
        await startCamera();
    }
};

const attachStreamToVideo = () => {
    if (!localStream.value) return;
    
    nextTick(() => {
        // We need to attach to whichever video element is active for user
        if (mainUserVideo.value) mainUserVideo.value.srcObject = localStream.value;
        if (pipUserVideo.value) pipUserVideo.value.srcObject = localStream.value;
    });
};

// Watch for layout swap to re-attach stream
watch(isUserMain, () => {
    attachStreamToVideo();
});

    const startFrameTransmission = () => {
    if (frameInterval) clearInterval(frameInterval);
    
    // Send frame every 200ms (5 FPS) - Increased for faster response
    frameInterval = setInterval(() => {
        if (!isCameraOn.value || !localStream.value) return;
        if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
        
        sendFrame();
    }, 200); 
};

const stopFrameTransmission = () => {
    if (frameInterval) clearInterval(frameInterval);
    frameInterval = null;
};

const sendFrame = () => {
    const videoEl = isUserMain.value ? mainUserVideo.value : pipUserVideo.value;
    if (!videoEl || !captureCanvas.value) return;
    
    const ctx = captureCanvas.value.getContext('2d');
    // Resize to smaller dimension to save bandwidth (e.g., 320x240)
    captureCanvas.value.width = 320;
    captureCanvas.value.height = 240;
    
    ctx.drawImage(videoEl, 0, 0, 320, 240);
    const base64Data = captureCanvas.value.toDataURL('image/jpeg', 0.6); // Low quality jpeg
    
    // Send special packet
    websocket.send(JSON.stringify({
        type: 'video_frame',
        data: base64Data
    }));
};


const mainAvatarSource = computed(() => {
  if (isPlayingAudio.value && !isVideoCallMode.value) {
    return videoPaths.talking;
  }
  if (loading.value) {
    return videoPaths.thinking;
  }
  return videoPaths.sleeping;
});

const videoAvatarSource = computed(() => {
  if (isPlayingAudio.value) {
    return videoPaths.talking;
  }
  return videoPaths.thinking;
});

// Deprecated: currentAvatarVideo (replaced by above)

const messages = ref([
  { role: 'assistant', content: '(～﹃～)~zZ' }
]);
const currentSessionId = ref('');
const userInput = ref('');
const loading = ref(false);
const messagesContainer = ref(null);
const fileInput = ref(null);
const attachedFiles = ref([]); // 存储已上传但未发送的文件信息
const ttsBuffer = ref(''); // 用于流式语音播放的缓冲
const ignoreWSAudio = ref(false); // 用于在打断后忽略旧的 WebSocket 音频片段

const avatarVideo = ref(null);
const avatarWrapper = ref(null);
const bgmAudio = ref(null);

// --- Draggable Logic ---
const avatarX = ref(20);
const avatarY = ref(window.innerHeight - 300); // Initial bottom-left position
const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });

const startDrag = (e) => {
  isDragging.value = true;
  dragOffset.value = {
    x: e.clientX - avatarX.value,
    y: e.clientY - avatarY.value
  };
  // Add global listeners
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
};

const onDrag = (e) => {
  if (!isDragging.value) return;
  
  let newX = e.clientX - dragOffset.value.x;
  let newY = e.clientY - dragOffset.value.y;
  
  // Boundary checks
  const maxX = window.innerWidth - 220; // tank width
  const maxY = window.innerHeight - 220;
  
  newX = Math.max(0, Math.min(newX, maxX));
  newY = Math.max(0, Math.min(newY, maxY));
  
  avatarX.value = newX;
  avatarY.value = newY;
};

const stopDrag = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
};

// 检查认证状态
const checkAuth = () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    router.push('/login');
    return false;
  }
  return true;
};

// Features state
const voiceOutputEnabled = ref(true);
const isRecording = ref(false);
const isRealTimeMode = ref(false);
let recognition = null;
let websocket = null;

// Avatars
const defaultUserAvatar = 'https://api.dicebear.com/9.x/adventurer/svg?seed=Zoey&hair=long01&hairColor=0e0e0e&skinColor=f2d3b1'; 
const defaultBotAvatar = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI1MCIgZmlsbD0iI2ZmYjZjMSIvPjxwYXRoIGQ9Ik0zMCA2MGMwIDEwIDEwIDIwIDIwIDIwczIwLTEwIDIwLTIwIiBzdHJva2U9IiMzMzMiIHN0cm9rZS13aWR0aD0iMyIgZmlsbD0ibm9uZSIvPjxjaXJjbGUgY3g9IjM1IiBjeT0iNDUiIHI9IjUiIGZpbGw9IiMzMzMiLz48Y2lyY2xlIGN4PSI2NSIgY3k9IjQ1IiByPSI1IiBmaWxsPSIjMzMzIi8+PHBhdGggZD0iTTEwIDMwQzEwIDMwIDIwIDEwIDUwIDEwczQwIDIwIDQwIDIwIiBzdHJva2U9IiMzMzMiIHN0cm9rZS13aWR0aD0iMyIgZmlsbD0ibm9uZSIvPjwvc3ZnPg=='; 

// 尝试加载本地头像，如果失败则回退到默认头像
const userAvatar = '/avatars/user.jpg';
const botAvatar = '/avatars/xibao.jpg';

const handleAvatarError = (event, type) => {
    // 避免无限循环
    const fallback = type === 'user' ? defaultUserAvatar : defaultBotAvatar;
    if (event.target.src !== fallback) {
        event.target.src = fallback;
    }
};

const isSidebarOpen = ref(false);
const sessions = ref([]);

const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value;
    if (isSidebarOpen.value) {
        fetchSessions();
    }
};

const fetchSessions = async () => {
    try {
        const response = await api.getSessions();
        sessions.value = response;
    } catch (error) {
        console.error("Failed to fetch sessions:", error);
    }
};

const startNewChat = () => {
    currentSessionId.value = '';
    messages.value = [
        { role: 'assistant', content: '(～﹃～)~zZ' }
    ];
    stopAllAudio(); // 停止语音
    if (abortController.value) { // 停止请求
        abortController.value.abort();
        abortController.value = null;
    }
    isSidebarOpen.value = false;
};

const loadSession = async (sessionId) => {
    if (currentSessionId.value === sessionId) return;
    
    // 切换会话前清理状态
    stopAllAudio();
    if (abortController.value) {
        abortController.value.abort();
        abortController.value = null;
    }

    loading.value = true;
    currentSessionId.value = sessionId;
    isSidebarOpen.value = false;
    
    try {
        const history = await api.getMessages(sessionId);
        // 转换历史消息格式
        messages.value = history.map(msg => ({
            role: msg.role,
            content: msg.content,
            type: msg.content.startsWith('http') || msg.content.startsWith('/uploads') || msg.content.startsWith('data:image') ? 'image' : 'text'
        }));
        
        // 滚动到底部
        scrollToBottom();
    } catch (error) {
        console.error("Failed to load session:", error);
    } finally {
        loading.value = false;
    }
};

const deleteSession = async (sessionId) => {
    if (!confirm('确定要删除这个对话吗？')) return;
    
    try {
        await api.deleteSession(sessionId);
        // 如果删除的是当前会话，开始新对话
        if (currentSessionId.value === sessionId) {
            startNewChat();
        }
        // 刷新列表
        fetchSessions();
    } catch (error) {
        console.error("Failed to delete session:", error);
        alert('删除失败，请重试');
    }
};

// Date formatter
const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// Time formatter
const formatTime = (date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
};

// --- BGM Control ---
const playBGM = () => {
    if (bgmAudio.value) {
        bgmAudio.value.volume = 0.2; // Set low volume for background
        bgmAudio.value.play().catch(e => {
            console.log("Autoplay prevented, waiting for user interaction");
            // Add one-time click listener to start BGM
            const startOnInteraction = () => {
                if (bgmAudio.value && !isVideoCallMode.value) {
                    bgmAudio.value.play();
                }
                document.removeEventListener('click', startOnInteraction);
            };
            document.addEventListener('click', startOnInteraction);
        });
    }
};

const pauseBGM = () => {
    if (bgmAudio.value) {
        bgmAudio.value.pause();
    }
};

// Watch video call mode to toggle BGM
watch(isVideoCallMode, (newVal) => {
    if (newVal) {
        pauseBGM();
    } else {
        playBGM();
    }
});

// 组件生命周期
onMounted(() => {
  // 检查认证状态
  checkAuth();
  
  // 滚动到底部
  scrollToBottom();

  // Start BGM
  playBGM();
});

// Scroll to bottom
const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// --- Real-Time Mode (WebSocket) ---
// 实时语音通话模式逻辑
// 使用 WebSocket 与后端建立双向通信：
// 发送：前端 Web Speech API 识别的文本
// 接收：后端流式返回的文本（用于显示）和音频数据（Base64，用于播放）
const toggleRealTimeMode = () => {
    if (isRealTimeMode.value) {
        stopRealTimeMode();
    } else {
        startRealTimeMode();
    }
};

const startRealTimeMode = () => {
    // Check if WS supported
    if (!('WebSocket' in window)) {
        alert('您的浏览器不支持 WebSocket');
        return;
    }
    
    // 开启前先停止所有正在播放的音频，避免混音
    stopAllAudio();
    
    // 强制开启语音输出
    voiceOutputEnabled.value = true;
    isRealTimeMode.value = true;
    
    // Connect WebSocket
    const token = localStorage.getItem('access_token');
    // Determine WS URL (assume same host, different protocol)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // 动态判断 Host
    let host;
    // import.meta.env.DEV 是 Vite 提供的环境变量，开发模式下为 true
    if (import.meta.env.DEV) {
        host = 'localhost:8000'; // 开发环境：直连后端
    } else {
        host = window.location.host; // 生产环境(Docker)：使用当前地址 (如 localhost:3000)，通过 Nginx 转发
    }
    
    const wsUrl = `${protocol}//${host}/api/ws/chat/${currentSessionId.value || 'new'}?token=${token}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
        console.log('WS Connected');
        // 连接成功后，立即开始语音识别（持续监听模式）
        stopRecording();
        startRecording();
    };
    
    websocket.onmessage = async (event) => {
        // Double check state
        if (!isRealTimeMode.value) return;

        try {
            const data = JSON.parse(event.data);
            
            // --- New: System Status ---
            if (data.type === 'system_status') {
                visionStatus.value = data.vision;
                console.log('Vision Status:', data.vision);
                return;
            }

            // --- New: Gesture Ack ---
            if (data.type === 'gesture_ack') {
                lastGesture.value = data.content;
                setTimeout(() => { lastGesture.value = ''; }, 3000);
                return;
            }
            
            // --- New: Hangup Command ---
            if (data.type === 'hangup') {
                stopVideoCall();
                return;
            }

            if (data.type === 'text') {
                // 如果是直接响应的手势文本，我们不需要在UI显示，只播放语音即可(由audio类型处理)
                if (data.is_direct) {
                    return; 
                }

                // 收到 'text' 类型消息：表示 AI 开始生成新的回复
                // 1. 重置 ignoreWSAudio，允许播放新的音频
                ignoreWSAudio.value = false;

                // 2. 确保 UI 上有一个 Assistant 的消息气泡用于追加内容
                const lastMsg = messages.value[messages.value.length - 1];
                if (!lastMsg || lastMsg.role !== 'assistant' || lastMsg.final) {
                     messages.value.push({ role: 'assistant', content: '' });
                }
                
                // 3. 追加文本内容
                const currentMsg = messages.value[messages.value.length - 1];
                currentMsg.content += data.content;
                scrollToBottom();
                
            } else if (data.type === 'audio') {
                // 收到 'audio' 类型消息：包含 TTS 生成的音频片段 (Base64)
                if (!isRealTimeMode.value) return; 
                
                // --- Priority Handling ---
                // 如果是直接响应（如手势），立即打断当前所有音频并播放
                if (data.is_direct) {
                    stopAllAudio();
                    ignoreWSAudio.value = false; // 确保允许播放
                } else {
                    // 如果当前处于“打断忽略”状态，丢弃该音频
                    if (ignoreWSAudio.value) return;
                }

                // 解码并加入播放队列
                const audioBlob = base64ToBlob(data.data, 'audio/mp3');
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                
                // 提高播放倍速，使对话更流畅
                audio.playbackRate = 1.25; 

                // 加入队列播放
                playAudioQueue(() => new Promise(resolve => {
                    // Check again before playing
                    if (!isRealTimeMode.value) {
                        URL.revokeObjectURL(audioUrl);
                        resolve();
                        return;
                    }

                    audio.onended = () => {
                        URL.revokeObjectURL(audioUrl);
                        resolve();
                    };
                    audio.play().catch(e => {
                        console.error("WS Audio play failed", e);
                        resolve();
                    });
                    currentAudio.value = audio;
                }));
            } else if (data.type === 'done') {
                // 收到 'done' 消息：表示本轮回复结束
                if (messages.value.length > 0) {
                    messages.value[messages.value.length - 1].final = true;
                }
            } else if (data.type === 'error') {
                console.error('WS Error:', data.message);
                alert('实时对话出错: ' + data.message);
                stopRealTimeMode();
            }
        } catch (e) {
            console.error('WS Message Parse Error', e);
        }
    };
    
    websocket.onclose = () => {
        console.log('WS Closed');
        if (isRealTimeMode.value) {
            // Unexpected close
            stopRealTimeMode();
        }
    };
    
    websocket.onerror = (e) => {
        console.error('WS Connection Error', e);
    };
};

const stopRealTimeMode = () => {
    isRealTimeMode.value = false;
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    stopRecording();
    stopAllAudio();
};

const base64ToBlob = (base64, mimeType) => {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
};

// --- Voice Input (Speech Recognition) ---
// 语音输入功能
// 使用浏览器原生 Web Speech API (SpeechRecognition)
// 注意：SpeechRecognition 在非 localhost 环境下通常需要 HTTPS
const toggleVoiceInput = () => {
  if (isRecording.value) {
    stopRecording();
  } else {
    startRecording();
  }
};

const startRecording = async () => {
  // 1. 检查浏览器支持
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('您的浏览器不支持语音输入，请使用 Chrome 或 Edge 浏览器。');
    return;
  }

  // 2. 检查安全上下文 (HTTPS 或 localhost)
  if (!window.isSecureContext) {
    alert(`当前环境不安全 (${window.location.origin})，浏览器禁止访问麦克风。\n请使用 https:// 或 http://localhost:端口 访问。`);
    return;
  }

  // 3. 尝试主动请求麦克风权限 (这通常能更有效地触发浏览器的弹窗)
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    console.error('Microphone permission denied via getUserMedia:', err);
    alert('无法获取麦克风权限。\n请点击地址栏左侧的“锁形图标”或“设置”图标，找到“麦克风”选项，并将其设置为【允许】(Allow)。\n设置后请刷新页面。');
    return;
  }
  
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  // 设置语言为中文
  recognition.lang = 'zh-CN'; 
  recognition.continuous = false; // 非连续模式，说完一句自动停止（除非在实时模式下被手动重启）
  recognition.interimResults = true; // 允许返回临时结果（实时显示说话内容）
  recognition.maxAlternatives = 1; 

  let initialInput = ''; // 记录开始录音时的已有文本

  recognition.onstart = () => {
    isRecording.value = true;
    initialInput = userInput.value; 
    console.log('Voice recognition started');
  };

  // 增加更多事件监听以排查问题
  recognition.onaudiostart = () => {
    console.log('Audio capturing started');
  };
  // ... 其他事件监听省略 ...

  recognition.onresult = (event) => {
    let interimTranscript = '';
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    // 实时通话模式下，只要检测到用户说话（包括中间结果），立即打断播报
    if (isRealTimeMode.value && (finalTranscript || interimTranscript)) {
        if (isPlayingAudio.value || audioQueue.value.length > 0) {
            console.log('User spoke, interrupting audio...');
            stopAllAudio();
        }
    }

    // 更新输入框：基础文本 + 已确认的语音 + 正在识别的语音
    if (finalTranscript || interimTranscript) {
        // 更新 initialInput 以累积最终结果
        if (finalTranscript) {
            initialInput += finalTranscript;
            
            // --- Real-Time Mode Logic ---
            // 确保 WebSocket 连接正常才发送
            if (isRealTimeMode.value && websocket && websocket.readyState === WebSocket.OPEN) {
                 stopAllAudio(); // 再次确保打断
                 
                 // 直接发送，不更新 userInput（避免文本框闪烁）
                 messages.value.push({ role: 'user', content: finalTranscript });
                 websocket.send(finalTranscript);
                 scrollToBottom();
                 
                 // 清空 buffer，防止后续非实时模式显示
                 initialInput = ''; 
            }
        }
        
        // 非实时模式下，只更新输入框显示
        if (!isRealTimeMode.value) {
             userInput.value = initialInput + interimTranscript;
        }
    }
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error', event.error);
    if (event.error === 'not-allowed') {
        alert('无法访问麦克风。\n原因：浏览器拒绝了权限请求。\n请检查地址栏左侧的权限设置，确保允许访问麦克风。');
    } else if (event.error === 'network') {
        alert('语音识别网络错误。\n请检查您的网络连接（Web Speech API 需要连接 Google 服务器），或尝试使用 Edge 浏览器。');
        console.warn('Network error in speech recognition');
    } else if (event.error === 'no-speech') {
        // 忽略未检测到语音的错误，只是停止录音
        console.log('No speech detected');
    } else {
        alert('语音识别发生错误: ' + event.error);
    }
    // ... 其他错误处理 ...
    
    if (!isRealTimeMode.value) {
        stopRecording();
    }
  };

  recognition.onend = () => {
    if (isRealTimeMode.value) {
        // 实时模式下，语音识别结束后自动重启，实现“永远在线”的听觉
        try {
            recognition.start();
        } catch (e) {
            console.log('Restarting recognition...');
        }
    } else {
        stopRecording();
    }
  };

  recognition.start();
};

const stopRecording = () => {
  isRecording.value = false;
  if (recognition) {
    // 移除所有事件监听，防止在 stop 后继续触发
    recognition.onresult = null;
    recognition.onend = null;
    recognition.onerror = null;
    recognition.stop();
    recognition = null;
  }
};

// --- Voice Output (TTS) ---
const toggleVoiceOutput = () => {
  voiceOutputEnabled.value = !voiceOutputEnabled.value;
  if (!voiceOutputEnabled.value) {
    stopAllAudio(); // 立即停止所有声音
  }
};

// --- Text Processing for TTS ---
// 文本清理函数：移除不适合朗读的内容
const cleanTextForTTS = (text) => {
    // 1. 去除 Markdown 图片链接
    let cleaned = text.replace(/!\[.*?\]\(.*?\)/g, '');
    
    // 2. 去除 Markdown 链接
    cleaned = cleaned.replace(/\[.*?\]\(.*?\)/g, '');
    
    // 3. 去除表情符号 (Emoji)
    // 匹配常见 Emoji 范围
    const emojiRegex = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu;
    cleaned = cleaned.replace(emojiRegex, '');
    
    // 4. 去除动作描述/心理活动，例如：(歪头)、[开心]、*笑*
    // 匹配 () [] （） 【】 ** "" “”
    // 使用 [\s\S] 替代 . 以匹配包括换行符在内的所有字符
    cleaned = cleaned.replace(/\([\s\S]*?\)|（[\s\S]*?）|\[[\s\S]*?\]|【[\s\S]*?】|\*[\s\S]*?\*|"[^"]*"|“[\s\S]*?”/g, '');
    
    // 5. 去除行尾未闭合的括号内容 (防止因断句导致朗读未闭合的动作描述)
    cleaned = cleaned.replace(/[\(（\[【“"][^）\)\]】”"]*$/g, '');
    
    return cleaned.trim();
};

const speak = async (text, append = false) => {
  if (!voiceOutputEnabled.value) return;

  // 如果不是追加模式，说明是新的一轮对话（或者需要打断之前的），清空队列
  if (!append) {
      stopAllAudio();
  }

  // 清理文本，去除表情和动作描述
  const textToSpeak = cleanTextForTTS(text);
  if (!textToSpeak) return; // 如果清理后为空（例如纯表情），则不朗读

  // 创建 Promise 并加入队列
  // 我们不等待 api.getTTS 完成，而是直接把处理过程放入队列
  // 这样可以实现"并行请求，串行播放"
  
  // 捕获当前的任务代数 (Generation ID)
  // 这是一个闭包变量，用于在异步任务执行时检查是否已被新的对话打断
  const currentGenId = audioGenerationId.value;

  const audioTask = async () => {
      // 任务开始执行时再次检查状态，如果已打断则不执行
      // 关键修改：检查 generationId 是否匹配，如果不匹配说明是旧的语音任务，直接丢弃
      if (currentGenId !== audioGenerationId.value) {
          console.log('Skipping audio task due to generation mismatch (Interrupted)');
          return;
      }
      
      if (audioQueue.value.length === 0 && !isPlayingAudio.value && !voiceOutputEnabled.value) {
          return;
      }

      try {
          const audioBlob = await api.getTTS(textToSpeak);
          
          // 获取 TTS 回来后再次检查，因为网络请求期间可能已经被打断
          if (currentGenId !== audioGenerationId.value) {
             console.log('Discarding TTS result due to generation mismatch (Interrupted)');
             return;
          }

          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          return new Promise((resolve) => {
              // 播放前再次检查
              if (!voiceOutputEnabled.value || currentGenId !== audioGenerationId.value) {
                  URL.revokeObjectURL(audioUrl);
                  resolve();
                  return;
              }

              audio.onended = () => {
                  URL.revokeObjectURL(audioUrl);
                  resolve();
              };
              
              // 播放并处理错误
              audio.play().catch(e => {
                  console.error("Audio play failed:", e);
                  resolve(); // 出错也视为完成，以免阻塞队列
              });
              
              // 存储当前播放的音频，以便中断
              currentAudio.value = audio;
          });
      } catch (error) {
          console.error("TTS Error:", error);
      }
  };

  playAudioQueue(audioTask);
};

// 音频队列管理
const audioQueue = ref([]); // 存储的是 async functions (tasks)
const isPlayingAudio = ref(false);
const currentAudio = ref(null); // 当前正在播放的 Audio 对象
const audioGenerationId = ref(0); // 音频生成代数，用于区分不同轮次的对话

// 将任务加入队列并尝试处理
const playAudioQueue = (task) => {
    audioQueue.value.push(task);
    processAudioQueue();
};

// 串行处理音频队列
const processAudioQueue = async () => {
    if (isPlayingAudio.value || audioQueue.value.length === 0) return;
    
    isPlayingAudio.value = true;
    const task = audioQueue.value.shift();
    
    try {
        await task(); // 等待播放完成
    } finally {
        isPlayingAudio.value = false;
        currentAudio.value = null;
        processAudioQueue(); // 继续下一个
    }
};

const stopAllAudio = () => {
    // 增加代数，立即使所有未完成的 TTS 请求失效
    // 这是解决"旧语音在打断后继续播放"问题的核心
    audioGenerationId.value++;
    // 标记忽略 WS 音频，直到新一轮文本开始
    ignoreWSAudio.value = true;

    // 停止当前播放
    if (currentAudio.value) {
        currentAudio.value.pause();
        currentAudio.value.currentTime = 0; // 重置进度
        // 关键：手动触发 ended 事件，确保 audioTask Promise 能被 resolve，避免 processAudioQueue 卡死
        currentAudio.value.dispatchEvent(new Event('ended'));
        currentAudio.value = null;
    }
    // 清空队列
    audioQueue.value = [];
    isPlayingAudio.value = false;
    // 清空缓冲
    ttsBuffer.value = '';
    // 取消浏览器语音 (如果还在用)
    window.speechSynthesis.cancel();
};

/* 
// 旧的浏览器 TTS (已废弃)
const speakBrowser = (text, append = false) => {
  if (!voiceOutputEnabled.value) return;
  if (!('speechSynthesis' in window)) return;

  // Cancel previous speech only if not appending (start of new turn)
  if (!append) {
      window.speechSynthesis.cancel();
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  // 语速调快，以匹配快速的文本生成 (1.5倍速)
  utterance.rate = 1.5; 
  window.speechSynthesis.speak(utterance);
};
*/

// --- File Upload ---
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 限制文件大小 (例如 10MB)
  if (file.size > 10 * 1024 * 1024) {
      alert('文件大小不能超过 10MB');
      return;
  }

  const formData = new FormData();
  formData.append('file', file);

  loading.value = true;
  try {
    const response = await api.uploadFile(formData);
    // response 结构: { filename, file_id, url, ... }
    // 注意：api.js 的响应拦截器已经提取了 response.data，所以这里直接使用 response
    
    // 添加到附件列表
    attachedFiles.value.push({
        type: 'image', // 暂时假设是图片，后续可以根据文件类型判断
        transfer_method: 'local_file', // 或者 'remote_url' 根据 Dify 要求
        url: response.url,
        upload_file_id: response.file_id,
        filename: response.filename
    });
    
    // 清空 input 以便重复上传同名文件
    event.target.value = '';
    
  } catch (error) {
    console.error('File upload failed:', error);
    alert('文件上传失败，请重试');
  } finally {
    loading.value = false;
  }
};

const removeAttachment = (index) => {
    attachedFiles.value.splice(index, 1);
};

const abortController = ref(null);

// --- Main Chat Logic ---
// 发送消息的主逻辑
// 包含：状态重置、附件处理、SSE 请求发起
const sendMessage = async () => {
  if ((!userInput.value.trim() && attachedFiles.value.length === 0) || loading.value) return;

  // 检查认证状态
  if (!checkAuth()) {
    return;
  }

  // 1. 中断旧的请求 (SSE)
  if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
  }
  
  // 2. 创建新的控制器
  abortController.value = new AbortController();

  const content = userInput.value;
  
  // 3. 停止之前的语音播放 (强制清空队列)
  stopAllAudio();
  
  // 处理附件显示
  if (attachedFiles.value.length > 0) {
      attachedFiles.value.forEach(file => {
          let displayUrl = file.url;
          if (displayUrl && !displayUrl.startsWith('http')) {
              displayUrl = `http://localhost:8000${displayUrl}`; 
          }

          messages.value.push({ 
              role: 'user', 
              content: displayUrl,
              type: 'image' 
          });
      });
  }

  if (content.trim()) {
      messages.value.push({ role: 'user', content });
  }
  
  // 暂存附件列表用于发送
  const filesToSend = [...attachedFiles.value];
  
  userInput.value = '';
  attachedFiles.value = []; // 清空预览区域
  loading.value = true;
  scrollToBottom();

  // 预先添加一个空的 assistant 消息用于流式接收
  messages.value.push({ 
      role: 'assistant', 
      content: '', 
      fullContent: '' 
  });
  const msgIndex = messages.value.length - 1;
  
  // 开启打字机效果 (视觉优化，使文字显示更平滑，不随网络包跳动)
  startTypewriter(msgIndex);

  // SSE 消息回调：每收到一个文本块触发一次
  const onMessage = (chunk) => {
      // console.log('ChatView received chunk:', chunk);
      
      const oldMsg = messages.value[msgIndex];
      const newFullContent = (oldMsg.fullContent || '') + chunk;
      
      // 更新 fullContent，打字机逻辑会负责更新 visible content
      messages.value[msgIndex] = {
          ...oldMsg,
          fullContent: newFullContent
      };
      
      // --- 流式语音逻辑 ---
      if (voiceOutputEnabled.value) {
          ttsBuffer.value += chunk;
          
          // 预处理：立即移除缓冲区中已经完整的动作描述，避免它们干扰断句或被意外朗读
          // 使用 [\s\S] 匹配跨行内容
          const removeRegex = /\([\s\S]*?\)|（[\s\S]*?）|\[[\s\S]*?\]|【[\s\S]*?】|\*[\s\S]*?\*|"[^"]*"|“[\s\S]*?”/g;
          ttsBuffer.value = ttsBuffer.value.replace(removeRegex, '');

          // 检查是否还在括号/引号内 (简单的奇偶校验或存在校验)
          // 如果缓冲区包含未闭合的开始符号，则暂停断句，等待闭合
          const hasOpenMarkers = /[\(（\[【“"]/.test(ttsBuffer.value);
          
          if (hasOpenMarkers) {
              // 简单的启发式：如果存在开始符号，且没有被上面的 removeRegex 清除（说明是不完整的），
              // 则我们假设正在接收一个动作描述，暂时不进行 TTS 断句
              // 注意：这可能会导致长句延迟，但能有效防止朗读动作描述
              // 风险：如果模型输出一个永远不闭合的符号，语音会卡住。
              // 兜底：如果缓冲区过长（例如超过 200 字符），强制断句
              if (ttsBuffer.value.length < 200) {
                  return; 
              }
          }

          // 简单的句子结束符匹配 (中文和英文)
          // 根据标点符号断句，实现"边生成边播放"
          const sentenceEndRegex = /([。！？；!?;]+|\n)/;
          const match = ttsBuffer.value.match(sentenceEndRegex);
          
          if (match) {
              const endIndex = match.index + match[0].length;
              const sentence = ttsBuffer.value.substring(0, endIndex);
              
              // 移除已处理的部分
              ttsBuffer.value = ttsBuffer.value.substring(endIndex);
              
              if (sentence.trim()) {
                  // append=true 意味着加入队列而不是打断
                  speak(sentence, true);
              }
          }
      }
  };

  // 监听会话 ID 更新 (解决记忆问题)
  // 后端如果检测到是新会话，会返回生成的 session_id
  onMessage.onSessionUpdate = (newId) => {
      // console.log('Session ID updated:', newId);
      currentSessionId.value = newId;
  };

  const onDone = () => {
    // console.log('ChatView SSE Done');
    loading.value = false;
    
    // 播放剩余的缓冲文本 (如果有)
    // 防止最后一句没有标点符号而被遗漏
    if (voiceOutputEnabled.value && ttsBuffer.value.trim()) {
        speak(ttsBuffer.value, true);
        ttsBuffer.value = '';
    }
  };

  const onError = (error) => {
    // ... error handling ...
    console.error('ChatView SSE Error:', error);
    loading.value = false;
    let errorMsg = '连接失败';
    
    // ... existing error logic ...
    if (typeof error === 'string' && error.includes('401')) {
        errorMsg = '登录已过期，请重新登录';
        localStorage.removeItem('access_token');
        setTimeout(() => {
            router.push('/login');
        }, 1500);
    } else if (error.message && error.message.includes('401')) {
        errorMsg = '登录已过期，请重新登录';
        localStorage.removeItem('access_token');
        setTimeout(() => {
            router.push('/login');
        }, 1500);
    } else if (typeof error === 'string') {
        errorMsg = error;
    } else if (error.message) {
        errorMsg = error.message;
    }
    
    // 追加错误信息
    if (messages.value[msgIndex]) {
        // 如果是错误，直接显示，不走打字机
        messages.value[msgIndex].content += `\n[错误: ${errorMsg}]`;
    }
    speak("发生错误: " + errorMsg);
  };

  try {
    await api.streamChat(
      { 
        message: content, 
        stream: true,
        session_id: currentSessionId.value, // 传递 session_id
        files: filesToSend // 传递附件
      }, 
      onMessage, 
      onDone, 
      onError,
      { signal: abortController.value.signal } // 传递 signal
    );
  } catch (error) {
    // 如果是 abort 造成的错误，忽略
    if (error.name === 'AbortError') {
        console.log('Request aborted');
        return;
    }
    onError(error);
  }
};

// --- Typewriter Effect Logic ---
let typewriterInterval = null;

const startTypewriter = (msgIndex) => {
    if (typewriterInterval) clearInterval(typewriterInterval);
    
    // 每 20ms 显示一个字符，稍微调快一点
    typewriterInterval = setInterval(() => {
        if (!messages.value[msgIndex]) {
            clearInterval(typewriterInterval);
            return;
        }

        // 简单的同步逻辑：如果音频队列堆积太多（说明语音说得慢），暂停文字显示等待一下
        // if (voiceOutputEnabled.value && audioQueue.value.length > 2) {
        //      return;
        // }
        const msg = messages.value[msgIndex];
        const fullContent = msg.fullContent || '';
        const currentContent = msg.content || '';
        
        if (currentContent.length < fullContent.length) {
            // 取下一个字符
            const nextChar = fullContent[currentContent.length];
            
            messages.value[msgIndex] = {
                ...msg,
                content: currentContent + nextChar
            };
            
            scrollToBottom();
        } else if (!loading.value && currentContent.length === fullContent.length) {
            // 如果加载完成且全部显示完毕，停止打字机
            clearInterval(typewriterInterval);
        }
    }, 20); 
};

// 在组件卸载时清除定时器
onUnmounted(() => {
    if (typewriterInterval) clearInterval(typewriterInterval);
});
</script>

<style scoped>
/* --- Fonts & Base --- */
@import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700&display=swap');

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #e0f7fa; /* 浅蓝底色 */
  color: #4a4a4a;
  font-family: 'M PLUS Rounded 1c', 'Microsoft YaHei', sans-serif;
  position: relative;
  overflow: hidden;
}

/* --- Ocean Background --- */
.ocean-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #b3e5fc 0%, #4fc3f7 50%, #0288d1 100%);
  z-index: 0;
  overflow: hidden;
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100px;
  background: url('data:image/svg+xml;utf8,<svg viewBox="0 0 1440 320" xmlns="http://www.w3.org/2000/svg"><path fill="rgba(255,255,255,0.2)" d="M0,192L48,197.3C96,203,192,213,288,229.3C384,245,480,267,576,250.7C672,235,768,181,864,181.3C960,181,1056,235,1152,234.7C1248,235,1344,181,1392,154.7L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>');
  background-size: cover;
  animation: waveMove 10s linear infinite;
  opacity: 0.6;
}

@keyframes waveMove {
  0% { transform: translateX(0) scaleY(1); }
  50% { transform: translateX(-20px) scaleY(1.1); }
  100% { transform: translateX(0) scaleY(1); }
}

.bubble-1, .bubble-2, .bubble-3 {
  position: absolute;
  bottom: -20px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  animation: floatUp infinite ease-in;
}

.bubble-1 { width: 40px; height: 40px; left: 10%; animation-duration: 8s; }
.bubble-2 { width: 20px; height: 20px; left: 20%; animation-duration: 12s; animation-delay: 2s; }
.bubble-3 { width: 60px; height: 60px; left: 80%; animation-duration: 15s; animation-delay: 1s; }

@keyframes floatUp {
  0% { transform: translateY(0); opacity: 0; }
  50% { opacity: 0.6; }
  100% { transform: translateY(-100vh); opacity: 0; }
}

/* --- Tech BG Removed --- */
/* .tech-bg { ... } */

/* --- Sidebar --- */
.sidebar-toggle {
  margin-right: 15px;
  font-size: 1.5rem;
}

.sidebar {
  position: absolute;
  top: 0;
  left: -280px;
  width: 280px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  z-index: 100;
  transition: left 0.3s ease;
  box-shadow: 2px 0 15px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}

.sidebar.open {
  left: 0;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e0ffff;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.sidebar-header h2 {
  margin: 0;
  color: #4682b4;
  font-size: 1.2rem;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #87ceeb 0%, #4682b4 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-weight: bold;
  transition: transform 0.2s;
}

.new-chat-btn:hover {
  transform: translateY(-2px);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.session-item {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
  border: 1px solid transparent;
  position: relative; /* 为删除按钮定位 */
}

.session-item:hover {
  background: #f0f8ff;
}

.session-item:hover .delete-session-btn {
  display: flex; /* 悬停时显示删除按钮 */
}

.session-item.active {
  background: #e0ffff;
  border-color: #87ceeb;
}

.delete-session-btn {
  display: none; /* 默认隐藏 */
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ff6b6b;
  color: white;
  border: none;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-session-btn:hover {
  background: #ff4757;
  transform: translateY(-50%) scale(1.1);
}

.session-title {
  display: block;
  font-weight: bold;
  color: #444;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-date {
  font-size: 0.75rem;
  color: #888;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.3);
  z-index: 90;
}

/* --- Header --- */
.chat-header {
  position: relative;
  z-index: 10;
  background: rgba(255, 255, 255, 0.8);
  padding: 15px 30px;
  box-shadow: 0 4px 20px rgba(135, 206, 235, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(15px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logo-wrapper {
  position: relative;
  transition: transform 0.3s;
}

.logo-wrapper:hover {
  transform: scale(1.1) rotate(5deg);
}

.header-logo {
  width: 55px;
  height: 55px;
  border-radius: 50%;
  border: 3px solid #87ceeb;
  background: #fff;
  padding: 2px;
  box-shadow: 0 4px 10px rgba(135, 206, 235, 0.4);
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 14px;
  height: 14px;
  background-color: #7cfc00;
  border: 3px solid #fff;
  border-radius: 50%;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(124, 252, 0, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(124, 252, 0, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(124, 252, 0, 0); }
}

.title-wrapper {
  display: flex;
  flex-direction: column;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
  color: #4682b4;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.subtitle {
  font-size: 0.8rem;
  color: #888;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.icon-btn {
  background: #fff;
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  color: #87ceeb;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(135, 206, 235, 0.4);
  color: #4682b4;
}

.icon-btn.active {
  background: #4682b4;
  color: #fff;
  box-shadow: 0 4px 12px rgba(70, 130, 180, 0.4);
}

/* --- Messages --- */
.messages-container {
  position: relative;
  z-index: 5;
  flex: 1;
  padding: 20px 30px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

.message-wrapper {
  display: flex;
  gap: 15px;
  max-width: 85%;
  animation: floatIn 0.4s ease-out;
}

@keyframes floatIn {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-wrapper.assistant {
  align-self: flex-start;
}

.avatar img {
  width: 45px;
  height: 45px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.message-wrapper:hover .avatar img {
  transform: scale(1.05) rotate(-2deg);
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bubble {
  padding: 14px 18px;
  border-radius: 18px;
  line-height: 1.6;
  position: relative;
  word-break: break-word;
  font-size: 0.95rem;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
  transition: all 0.2s;
}

.user .bubble {
  background: linear-gradient(135deg, #ff9a9e 0%, #ff69b4 100%);
  color: #fff;
  border-top-right-radius: 4px;
}

.assistant .bubble {
  background: #fff;
  color: #444;
  border-top-left-radius: 4px;
  border: 1px solid rgba(255, 182, 193, 0.3);
}

.uploaded-image {
  max-width: 100%;
  max-height: 300px;
  border-radius: 12px;
  margin-top: 5px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.timestamp {
  font-size: 0.7rem;
  color: #aaa;
  margin: 0 5px;
}

.user .timestamp {
  text-align: right;
}

/* --- Typing Indicator --- */
.loading-bubble {
  background: #fff;
  padding: 15px 20px;
  border-radius: 18px;
  border-top-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.typing-indicator span {
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #ffb6c1;
  border-radius: 50%;
  margin: 0 3px;
  animation: typing 1s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; background-color: #ff69b4; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; background-color: #ff1493; }

@keyframes typing {
  0%, 100% { transform: scale(0.6); opacity: 0.6; }
  50% { transform: scale(1); opacity: 1; }
}

/* --- Input Area --- */
.input-area {
  position: relative;
  z-index: 10;
  padding: 20px 30px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 -5px 20px rgba(0,0,0,0.02);
}

.attachments-preview {
  display: flex;
  gap: 10px;
  padding: 0 5px 12px;
  flex-wrap: wrap;
}

.attachment-chip {
  background: #fff;
  border: 1px solid #87ceeb;
  border-radius: 20px;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #4682b4;
  box-shadow: 0 2px 5px rgba(135, 206, 235, 0.2);
}

.remove-btn {
  cursor: pointer;
  color: #00bfff;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0, 191, 255, 0.1);
  font-size: 0.7rem;
}

.glass-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 1000px;
  margin: 0 auto;
  background: #fff;
  padding: 8px 12px;
  border-radius: 24px;
  border: 2px solid #e0ffff;
  box-shadow: 0 5px 20px rgba(135, 206, 235, 0.25);
  transition: all 0.3s;
}

.glass-panel:focus-within {
  border-color: #87ceeb;
  box-shadow: 0 8px 25px rgba(135, 206, 235, 0.4);
  transform: translateY(-2px);
}

.tech-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #4a4a4a;
  font-family: 'M PLUS Rounded 1c', sans-serif;
  font-size: 1rem;
  outline: none;
  padding: 8px;
  min-height: 24px;
}

.tech-input::placeholder {
  color: #bbb;
}

.action-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  background: #e0ffff;
  color: #4682b4;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #87ceeb;
  color: #fff;
  transform: scale(1.05);
}

.action-btn.recording {
  background: #ff4757;
  color: #fff;
  animation: pulse 1.5s infinite;
}

.action-btn.active {
  background: #4682b4;
  color: #fff;
  box-shadow: 0 4px 12px rgba(70, 130, 180, 0.4);
}

.send-btn {
  padding: 0 24px;
  height: 42px;
  border-radius: 21px;
  border: none;
  background: linear-gradient(135deg, #87ceeb 0%, #4682b4 100%);
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 10px rgba(70, 130, 180, 0.3);
  display: flex;
  align-items: center;
  gap: 6px;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(70, 130, 180, 0.4);
}

.send-btn:disabled {
  background: #eee;
  color: #aaa;
  cursor: not-allowed;
  box-shadow: none;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #87ceeb;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #4682b4;
}

/* Video Avatar Wrapper (Water Tank) */
.video-avatar-wrapper {
  position: absolute;
  /* top/left set by inline style */
  z-index: 100; /* High z-index to float above everything */
  pointer-events: auto;
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.video-avatar-wrapper:active {
  cursor: grabbing;
}

.water-tank {
  width: 220px;
  height: 220px;
  border-radius: 50%; /* 圆形水缸 */
  position: relative;
  overflow: hidden;
  background: rgba(135, 206, 250, 0.2);
  border: 4px solid rgba(255, 255, 255, 0.4);
  box-shadow: 
    0 0 20px rgba(0, 191, 255, 0.4),
    inset 0 0 30px rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(2px);
  animation: tankFloat 6s ease-in-out infinite;
}

@keyframes tankFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.avatar-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* 边缘羽化，避免贴图感 */
  mask-image: radial-gradient(circle, black 60%, transparent 100%);
  -webkit-mask-image: radial-gradient(circle, black 60%, transparent 100%);
  transform: scale(1.1); /* 稍微放大以配合羽化 */
}

/* 高光效果 */
.tank-highlight {
  position: absolute;
  top: 15%;
  left: 15%;
  width: 30%;
  height: 20%;
  background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.8) 0%, transparent 70%);
  transform: rotate(-45deg);
  opacity: 0.6;
  pointer-events: none;
}

.tank-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, transparent 50%, rgba(0, 191, 255, 0.1) 100%);
  pointer-events: none;
}

/* --- Video Call Overlay --- */
.video-call-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.video-container {
  position: relative;
  width: 100%;
  max-width: 600px;
  aspect-ratio: 1 / 1; /* Square shape as requested */
  background: #000;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 0 50px rgba(135, 206, 235, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Main Video fills the container */
.main-video-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.main-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Mirror user camera */
.user-cam {
  transform: scaleX(-1);
}

/* Picture-in-Picture (Small Video) */
.pip-video-wrapper {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 120px;
  height: 120px;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 5px 15px rgba(0,0,0,0.5);
  border: 2px solid rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: transform 0.3s;
  z-index: 10;
}

.pip-video-wrapper:hover {
  transform: scale(1.05);
  border-color: #87ceeb;
}

.pip-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Controls */
.video-controls {
  position: absolute;
  bottom: 30px;
  left: 0;
  width: 100%;
  display: flex;
  justify-content: center;
  gap: 20px;
  z-index: 20;
}

.control-btn {
  padding: 12px 24px;
  border-radius: 30px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(5px);
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.control-btn.close-btn {
  background: #ff4757;
}

.control-btn.close-btn:hover {
  background: #ff6b81;
}

.control-btn.off {
  background: rgba(0, 0, 0, 0.5);
  color: #aaa;
}

/* Gesture Toast */
.gesture-toast {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.9rem;
  pointer-events: none;
  animation: fadeInOut 3s forwards;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.vision-status {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.5);
  color: #ff4d4f; /* Default red */
  padding: 5px 10px;
  border-radius: 15px;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 5px;
  z-index: 10;
}

.vision-status.active {
  color: #52c41a; /* Green */
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -10px); }
  10% { opacity: 1; transform: translate(-50%, 0); }
  90% { opacity: 1; transform: translate(-50%, 0); }
  100% { opacity: 0; transform: translate(-50%, -10px); }
}
</style>
