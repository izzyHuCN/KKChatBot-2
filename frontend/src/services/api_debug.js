import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

console.log('🔧 API Base URL:', API_BASE_URL)

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
    console.log('📝 Request Interceptor - Token:', token ? 'Present' : 'Missing')
    
    if (token) {
      // 确保Authorization头被正确设置
      config.headers.Authorization = `Bearer ${token}`
      console.log('🔑 Authorization header set:', config.headers.Authorization.substring(0, 20) + '...')
    } else {
      console.log('⚠️ No token found, request will likely fail')
      // 如果没有token，尝试跳转到登录页
      if (window.location.pathname !== '/login') {
        console.log('🔄 Redirecting to login...')
        window.location.href = '/login'
      }
    }
    
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
    console.log('✅ Response success:', response.status, response.config.url)
    return response.data
  },
  (error) => {
    console.error('❌ Response error:', error.response?.status, error.config?.url)
    
    if (error.response) {
      const status = error.response.status
      
      if (status === 401 || status === 403) {
        console.log(`🚫 Authentication failed (${status}), clearing token and redirecting...`)
        localStorage.removeItem('access_token')
        
        // 延迟重定向，让用户看到错误信息
        setTimeout(() => {
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }, 1000)
      }
    }
    
    return Promise.reject(error)
  }
)

export default {
  // 认证相关
  login: (credentials) => {
    console.log('🔐 Attempting login...')
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
  sendMessage: (data) => {
    console.log('💬 Sending message:', data.message)
    return api.post('/api/chat', data)
  },
  
  getSessions: () => api.get('/api/sessions'),
  getMessages: (sessionId) => api.get(`/api/messages/${sessionId}`),
  
  // 文件上传
  uploadFile: (formData) => api.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}