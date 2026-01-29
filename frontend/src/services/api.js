import axios from 'axios'

const API_BASE_URL = '' // Empty string to use relative path for proxy


const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
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

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  // 认证相关
  login: (credentials) => {
    // 将JSON转换为URL编码格式
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

  // 聊天相关
  sendMessage: (data) => api.post('/api/chat', data),
  
  // 流式聊天 (SSE)
  // 返回一个 Promise，该 Promise 在流开始时解决，并提供一个回调函数来接收数据
  streamChat: async (data, onMessage, onDone, onError, options = {}) => {
    const token = localStorage.getItem('access_token');
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data),
        signal: options.signal // 支持 AbortController
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // 保留最后一个不完整的块
        
        for (const line of lines) {
          // console.log('[SSE RAW]', line); // 打印原始行
          if (line.trim().startsWith('data:')) {
            try {
              const jsonStr = line.substring(line.indexOf('data:') + 5).trim();
              
              if (!jsonStr) continue;
              
              const eventData = JSON.parse(jsonStr);
              // console.log('[SSE Parsed]', eventData); // 打印解析后的对象
              
              if (eventData.event === 'message') {
                if (eventData.answer) {
                    onMessage(eventData.answer);
                } else {
                    console.warn('[SSE Warning] Empty answer in message event', eventData);
                }
              } else if (eventData.event === 'session_update') {
                if (onMessage.onSessionUpdate) {
                    onMessage.onSessionUpdate(eventData.session_id);
                }
              } else if (eventData.event === 'done') {
                // console.log('[SSE] Stream done');
                if (onDone) onDone();
              } else if (eventData.event === 'error') {
                console.error('[SSE Error]', eventData.message);
                if (onError) onError(eventData.message);
              } else {
                // console.log('[SSE] Unhandled event type:', eventData.event);
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
  
  // 文件上传
  uploadFile: (formData) => api.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),

  // 文本转语音
  getTTS: async (text) => {
    try {
        // 直接使用 axios 实例发送请求
        // 注意：这里的拦截器会返回 response.data
        // 当 responseType 为 'blob' 时，response.data 就是 Blob 对象
        return await api.post('/api/tts', { text }, {
          responseType: 'blob' 
        });
    } catch (error) {
        console.error("API Error in getTTS:", error);
        throw error;
    }
  }
}
