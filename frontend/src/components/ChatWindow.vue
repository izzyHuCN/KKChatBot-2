<template>
  <div class="chat-container">
    <!-- 会话侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>对话历史</h3>
        <el-button type="primary" @click="createNewSession" size="small">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="switchSession(session.id)"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-title">{{ session.title || '新对话' }}</span>
          <span class="session-time">{{ formatTime(session.updated_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 聊天主区域 -->
    <div class="chat-main">
      <!-- 消息区域 -->
      <div class="messages-container" ref="messagesContainer">
        <!-- DEBUG INFO -->
        <div v-if="debugInfo" style="padding: 10px; background: #eee; color: red; font-size: 12px; white-space: pre-wrap;">
            DEBUG: {{ debugInfo }}
        </div>
        
        <div v-for="(message, index) in messages" :key="index" class="message-wrapper">
          <div :class="['message', message.role]">
            <div class="avatar">
              <el-icon v-if="message.role === 'user'"><User /></el-icon>
              <el-icon v-else><Robot /></el-icon>
            </div>
            <div class="content">
              <!-- Fallback to text if markdown fails or for debugging -->
              <div v-if="message.role === 'assistant'" class="markdown-content">
                 <div v-html="renderMarkdown(message.content)"></div>
                 <div v-if="!message.content" style="color: #999;">(Empty...)</div>
              </div>
              <div v-else class="text-content">{{ message.content }}</div>
              <div class="time">{{ formatMessageTime(message.created_at) }}</div>
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="isLoading" class="message assistant">
          <div class="avatar">
            <el-icon><Robot /></el-icon>
          </div>
          <div class="content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-container">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="输入您的问题..."
            @keydown.enter.exact.prevent="sendMessage"
          />
          <div class="input-actions">
            <el-button
              type="primary"
              :loading="isLoading"
              @click="sendMessage"
              :disabled="!inputMessage.trim()"
            >
              发送
            </el-button>
          </div>
        </div>
        <div class="input-tips">
          <small>按 Enter 发送，Shift + Enter 换行</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import api from '@/services/api'
import {
  Plus,
  ChatDotRound,
  User,
  Robot
} from '@element-plus/icons-vue'

// 数据
const sessions = ref([])
const messages = ref([])
const currentSessionId = ref('')
const inputMessage = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)
const isRecording = ref(false)
const isInternalSessionUpdate = ref(false)
const debugInfo = ref('')
let recognition = null

// 配置marked
marked.setOptions({
  highlight: function(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  },
  breaks: true
})

// 渲染markdown
const renderMarkdown = (content) => {
  return marked(content)
}

// 时间格式化
const formatTime = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date

  if (diff < 24 * 60 * 60 * 1000) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

const formatMessageTime = (dateString) => {
  return new Date(dateString).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// --- Voice Input Logic ---
const toggleVoiceInput = () => {
  if (isRecording.value) {
    stopVoiceInput()
  } else {
    startVoiceInput()
  }
}

const startVoiceInput = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    ElMessage.error('您的浏览器不支持语音输入，请使用 Chrome 或 Edge 浏览器')
    return
  }
  
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = true // 开启临时结果，提升响应感
  
  recognition.onstart = () => {
    console.log('Voice recognition started')
    isRecording.value = true
  }
  
  recognition.onend = () => {
    console.log('Voice recognition ended')
    isRecording.value = false
  }
  
  recognition.onresult = (event) => {
    const lastResult = event.results[event.results.length - 1]
    const transcript = lastResult[0].transcript
    console.log('Voice result:', transcript, 'Final:', lastResult.isFinal)
    
    if (lastResult.isFinal) {
        inputMessage.value += transcript
    }
  }
  
  recognition.onerror = (event) => {
    console.error('Speech recognition error', event.error)
    isRecording.value = false
    if (event.error === 'not-allowed') {
        ElMessage.error('无法访问麦克风，请检查权限设置')
    } else if (event.error !== 'no-speech') {
        ElMessage.error('语音识别失败: ' + event.error)
    }
  }
  
  try {
    recognition.start()
  } catch (e) {
    console.error('Start recognition failed:', e)
    ElMessage.error('启动语音识别失败')
  }
}

const stopVoiceInput = () => {
  if (recognition) {
    recognition.stop()
  }
  isRecording.value = false
}

// --- Main Chat Logic ---
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return

  // 检查认证状态
  if (!checkAuth()) {
    return
  }

  // 添加用户消息到界面
  messages.value.push({
    role: 'user',
    content: message,
    created_at: new Date().toISOString()
  })

  // 清空输入框
  userInput.value = ''
  // 兼容两种输入框变量名 (userInput vs inputMessage) - 之前的代码混用了
  inputMessage.value = ''

  // 滚动到底部
  scrollToBottom()

  // 设置加载状态
  loading.value = true
  
  // 1. 先 push 到数组
  messages.value.push({
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString()
  })
  
  // 2. 获取当前消息的索引
  const msgIndex = messages.value.length - 1

  // 定义回调函数
  const onMessage = (chunk) => {
    console.log('Vue onMessage received chunk:', chunk); // Debug log
    // 强制触发更新：使用对象替换方式
    if (messages.value[msgIndex]) {
        const oldMsg = messages.value[msgIndex]
        // 创建新对象以确保引用变化，强制 Vue 更新
        messages.value[msgIndex] = {
            ...oldMsg,
            content: oldMsg.content + chunk
        }
        debugInfo.value = `Rx: ${chunk.length} chars. Total: ${messages.value[msgIndex].content.length}`
    } else {
        console.error('Message index not found:', msgIndex);
    }
    scrollToBottom()
  }
  
  // 处理会话 ID 更新
  onMessage.onSessionUpdate = (newId) => {
      if (!currentSessionId.value || currentSessionId.value !== newId) {
          console.log('Updating Session ID:', newId)
          currentSessionId.value = newId
          loadSessions() // 刷新列表以显示新标题
      }
  }

  const onDone = () => {
    loading.value = false
    // 如果是新会话且 ID 没更新（防抖），再次检查
    if (!currentSessionId.value) {
        loadSessions()
    }
  }

  const onError = (err) => {
    console.error('Chat error:', err)
    let errorMsg = '连接中断'
    
    if (typeof err === 'string') {
        errorMsg = err
    } else if (err.message) {
        errorMsg = err.message
    }
    
    messages.value[assistantMsgIndex].content += `\n[错误: ${errorMsg}]`
    loading.value = false
    speak("发生错误，请重试")
  }

  try {
    // 使用流式 API
    await api.streamChat(
      {
        message,
        session_id: currentSessionId.value,
        stream: true
      },
      onMessage,
      onDone,
      onError
    )
  } catch (error) {
    onError(error)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 创建新会话
const createNewSession = () => {
  currentSessionId.value = ''
  messages.value = []
  inputMessage.value = ''
}

// 切换会话
const switchSession = async (sessionId) => {
  if (sessionId === currentSessionId.value) return

  currentSessionId.value = sessionId
  await loadMessages(sessionId)
}

// 加载会话列表
const loadSessions = async () => {
  try {
    const response = await api.getSessions()
    sessions.value = response
  } catch (error) {
    console.error('加载会话失败:', error)
  }
}

// 加载消息
const loadMessages = async (sessionId) => {
  try {
    const response = await api.getMessages(sessionId)
    messages.value = response
    scrollToBottom()
  } catch (error) {
    console.error('加载消息失败:', error)
  }
}

// 监听会话ID变化
watch(currentSessionId, (newSessionId) => {
  if (newSessionId) {
    loadMessages(newSessionId)
  }
})

// 组件挂载
onMounted(async () => {
  await loadSessions()
  // 如果没有会话，创建一个新的
  if (sessions.value.length === 0) {
    createNewSession()
  } else {
    currentSessionId.value = sessions.value[0].id
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background-color 0.2s;
}

.session-item:hover {
  background-color: #f9f9f9;
}

.session-item.active {
  background-color: #e8f4ff;
  border-left: 3px solid #409eff;
}

.session-title {
  flex: 1;
  font-size: 14px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 12px;
  color: #999;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #409eff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .avatar {
  background: #67c23a;
}

.content {
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  max-width: 100%;
}

.message.user .content {
  background: #95d475;
  color: white;
}

.markdown-content {
  font-size: 14px;
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(p) {
  margin: 0.5em 0;
}

.markdown-content :deep(code) {
  background: #f6f8fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.markdown-content :deep(pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 20px;
  margin: 0.5em 0;
}

.time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.input-container {
  padding: 20px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.input-wrapper {
  display: flex;
  gap: 12px;
}

.input-actions {
  display: flex;
  align-items: flex-end;
}

.input-tips {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}
</style>