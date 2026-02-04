import axios from 'axios'

// API 基础路径
// 在开发环境中 (vite.config.js) 配置了代理，将 /api 转发到 localhost:8000
// 生产环境应指向实际的后端域名
const API_BASE_URL = '' 


const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// --- 请求拦截器 ---
// 在发送请求前自动附加 JWT Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// --- 响应拦截器 ---
// 统一处理响应数据和认证错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401/403 表示 Token 过期或无效，强制跳转登录页
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  // --- 认证相关 ---
  login: (credentials) => {
    // FastAPI OAuth2PasswordRequestForm 需要 x-www-form-urlencoded 格式
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
  },
  register: (userData) => api.post('/auth/register', userData),

  // --- 聊天相关 ---
  sendMessage: (data) => api.post('/api/chat', data),
  
  /**
   * 流式聊天 (SSE - Server-Sent Events)
   * 
   * @param {Object} data - 请求数据 { message: "hello", session_id: "...", files: [...] }
   * @param {Function} onMessage - 接收到文本片段时的回调
   * @param {Function} onDone - 流结束时的回调
   * @param {Function} onError - 出错时的回调
   * @param {Object} options - 额外选项，如 { signal: AbortSignal } 用于取消请求
   */
  streamChat: async (data, onMessage, onDone, onError, options = {}) => {
    const token = localStorage.getItem('access_token');
    
    try {
      // 使用 fetch API 以便处理流式响应 (axios 对流的支持不如 fetch 原生)
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data),
        signal: options.signal // 支持 AbortController 打断请求
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 获取 ReadableStream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        // 解码二进制流为文本
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        // 处理可能粘连的数据块 (SSE 格式: data: {...}\n\n)
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // 保留最后一个不完整的块
        
        for (const line of lines) {
          if (line.trim().startsWith('data:')) {
            try {
              const jsonStr = line.substring(line.indexOf('data:') + 5).trim();
              
              if (!jsonStr) continue;
              
              const eventData = JSON.parse(jsonStr);
              
              // 根据事件类型分发处理
              if (eventData.event === 'message') {
                if (eventData.answer) {
                    onMessage(eventData.answer);
                }
              } else if (eventData.event === 'session_update') {
                // 后端通知更新 session_id (特别是新会话创建时)
                if (onMessage.onSessionUpdate) {
                    onMessage.onSessionUpdate(eventData.session_id);
                }
              } else if (eventData.event === 'done') {
                if (onDone) onDone();
              } else if (eventData.event === 'error') {
                console.error('[SSE Error]', eventData.message);
                if (onError) onError(eventData.message);
              }
            } catch (e) {
              console.warn('Failed to parse SSE event:', e, line);
            }
          }
        }
      }
    } catch (error) {
      if (onError) onError(error);
    }
  },

  getSessions: () => api.get('/api/sessions'),
  getMessages: (sessionId) => api.get(`/api/messages/${sessionId}`),
  deleteSession: (sessionId) => api.delete(`/api/sessions/${sessionId}`),
  
  // --- 文件上传 ---
  uploadFile: (formData) => api.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),

  // --- 文本转语音 (TTS) ---
  getTTS: async (text) => {
    try {
        // 请求返回的是二进制音频流 (Blob)
        return await api.post('/api/tts', { text }, {
          responseType: 'blob' 
        });
    } catch (error) {
        console.error("API Error in getTTS:", error);
        throw error;
    }
  }
}
