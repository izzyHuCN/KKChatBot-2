import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

console.log('🔧 API Base URL:', API_BASE_URL)

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 🔒 请求拦截器 - 确保每次都正确添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    console.log('🔍 Request Interceptor - Checking token...')
    
    if (token) {
      console.log('✅ Token found, adding to headers')
      config.headers.Authorization = `Bearer ${token}`
    } else {
      console.log('⚠️ No token found')
    }
    
    console.log(`📤 ${config.method?.toUpperCase()} ${config.url}`)
    console.log('Headers:', config.headers)
    
    return config
  },
  (error) => {
    console.error('❌ Request interceptor error:', error)
    return Promise.reject(error)
  }
)

// 🔍 响应拦截器 - 增强错误处理
api.interceptors.response.use(
  (response) => {
    console.log(`✅ Response: ${response.status} ${response.config.url}`)
    return response.data
  },
  (error) => {
    console.error('❌ Response error:', {
      status: error.response?.status,
      url: error.config?.url,
      data: error.response?.data
    })
    
    if (error.response) {
      const status = error.response.status
      
      if (status === 401 || status === 403) {
        console.log(`🚫 Authentication failed (${status}), clearing token`)
        localStorage.removeItem('access_token')
        
        // 延迟重定向，让用户看到错误信息
        setTimeout(() => {
          if (window.location.pathname !== '/login') {
            console.log('🔄 Redirecting to login...')
            window.location.href = '/login'
          }
        }, 1000)
      }
    }
    
    return Promise.reject(error)
  }
)

// 认证相关API
export const authAPI = {
  login: async (credentials) => {
    console.log('🔐 Attempting login...')
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    try {
      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      console.log('✅ Login successful')
      
      if (response.access_token) {
        localStorage.setItem('access_token', response.access_token)
        console.log('💾 Token saved to localStorage')
      }
      
      return response
    } catch (error) {
      console.error('❌ Login failed:', error)
      throw error
    }
  },
  
  register: (userData) => {
    console.log('📝 Registering user...')
    return api.post('/auth/register', userData)
  },
  
  logout: () => {
    console.log('🚪 Logging out...')
    localStorage.removeItem('access_token')
  },
  
  getToken: () => {
    return localStorage.getItem('access_token')
  },
  
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token')
  }
}

// 聊天相关API
export const chatAPI = {
  sendMessage: async (data) => {
    console.log('💬 Sending message:', data.message)
    
    if (!authAPI.isAuthenticated()) {
      throw new Error('User not authenticated')
    }
    
    return api.post('/api/chat', data)
  },
  
  getSessions: () => {
    console.log('📋 Getting sessions...')
    return api.get('/api/sessions')
  },
  
  getMessages: (sessionId) => {
    console.log(`📨 Getting messages for session: ${sessionId}`)
    return api.get(`/api/messages/${sessionId}`)
  }
}

// 文件上传API
export const uploadAPI = {
  uploadFile: (formData) => {
    console.log('📁 Uploading file...')
    return api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}

// 默认导出兼容旧代码
export default {
  ...authAPI,
  ...chatAPI,
  ...uploadAPI
}