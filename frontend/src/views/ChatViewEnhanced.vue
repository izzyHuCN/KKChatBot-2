<template>
  <div class="chat-container">
    <div class="header">
      <div class="title">KKChatBot-2</div>
      <div class="subtitle">AI 助手</div>
      <div class="auth-status">
        <span :class="{ 'authenticated': isAuthenticated, 'not-authenticated': !isAuthenticated }">
          {{ authStatusText }}
        </span>
        <button @click="checkAuthStatus" class="refresh-auth">🔄</button>
      </div>
    </div>
    
    <div class="messages-container" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role]">
        <div class="message-content">{{ message.content }}</div>
        <div class="message-time">{{ formatTime(new Date()) }}</div>
      </div>
      <div v-if="loading" class="loading-indicator">
        <span>🤖 AI 思考中...</span>
      </div>
    </div>
    
    <div class="input-area">
      <input 
        v-model="userInput" 
        @keyup.enter="sendMessage" 
        placeholder="输入消息..."
        :disabled="loading || !isAuthenticated"
        class="message-input"
      />
      <button @click="sendMessage" :disabled="loading || !isAuthenticated" class="send-button">
        {{ loading ? '发送中...' : '发送' }}
      </button>
      <button @click="logout" class="logout-button">🚪 登出</button>
    </div>
    
    <div v-if="!isAuthenticated" class="auth-overlay">
      <div class="auth-prompt">
        <h3>🔒 需要登录</h3>
        <p>请先登录以使用聊天功能</p>
        <button @click="goToLogin" class="login-button">前往登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
const messages = ref([
  { role: 'assistant', content: '系统初始化完成。我是 KKChatBot-2，请下达指令。' }
]);
const userInput = ref('');
const loading = ref(false);
const messagesContainer = ref(null);
const isAuthenticated = ref(false);
const authStatusText = computed(() => isAuthenticated.value ? '✅ 已认证' : '❌ 未认证');

// 认证状态检查
const checkAuthStatus = () => {
  console.log('🔍 检查认证状态...');
  const token = localStorage.getItem('access_token');
  
  if (token) {
    console.log('✅ Token存在:', token.substring(0, 20) + '...');
    isAuthenticated.value = true;
    return true;
  } else {
    console.log('❌ Token不存在');
    isAuthenticated.value = false;
    return false;
  }
};

// 前往登录页
const goToLogin = () => {
  console.log('🔄 跳转到登录页...');
  router.push('/login');
};

// 登出
const logout = () => {
  console.log('🚪 用户登出');
  localStorage.removeItem('access_token');
  isAuthenticated.value = false;
  messages.value.push({ 
    role: 'assistant', 
    content: '您已登出，请重新登录以继续使用。' 
  });
  
  setTimeout(() => {
    router.push('/login');
  }, 1500);
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || loading.value) return;
  
  // 再次检查认证状态
  if (!checkAuthStatus()) {
    console.log('⚠️ 未认证，阻止发送消息');
    messages.value.push({ 
      role: 'assistant', 
      content: '请先登录后再发送消息。' 
    });
    return;
  }

  console.log('💬 准备发送消息:', userInput.value);
  
  const content = userInput.value;
  messages.value.push({ role: 'user', content });
  userInput.value = '';
  loading.value = true;
  
  await scrollToBottom();

  try {
    console.log('🚀 调用API发送消息...');
    const response = await api.sendMessage({ message: content });
    console.log('✅ API响应成功:', response);
    
    messages.value.push({ role: 'assistant', content: response.message });
    
  } catch (error) {
    console.error('❌ API调用失败:', error);
    
    if (error.response) {
      if (error.response.status === 401 || error.response.status === 403) {
        console.log('🚫 认证失败，清除token');
        localStorage.removeItem('access_token');
        isAuthenticated.value = false;
        
        messages.value.push({ 
          role: 'assistant', 
          content: '认证失败，请重新登录。' 
        });
        
        setTimeout(() => {
          router.push('/login');
        }, 2000);
      } else {
        messages.value.push({ 
          role: 'assistant', 
          content: `错误: ${error.response.data?.detail || '未知错误'}` 
        });
      }
    } else {
      messages.value.push({ 
        role: 'assistant', 
        content: '网络错误，请检查连接。' 
      });
    }
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
};

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 时间格式化
const formatTime = (date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
};

// 组件生命周期
onMounted(() => {
  console.log('🚀 ChatView组件挂载');
  checkAuthStatus();
  
  if (!isAuthenticated.value) {
    console.log('⚠️ 组件挂载时未认证');
    // 给一点时间显示未认证状态，然后跳转
    setTimeout(() => {
      if (!isAuthenticated.value) {
        console.log('🔄 自动跳转到登录页');
        router.push('/login');
      }
    }, 3000);
  }
  
  scrollToBottom();
});

onUnmounted(() => {
  console.log('🏁 ChatView组件卸载');
});
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  position: relative;
}

.header {
  background: #2c3e50;
  color: white;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 20px;
  font-weight: bold;
}

.subtitle {
  font-size: 14px;
  opacity: 0.8;
}

.auth-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.authenticated {
  color: #4CAF50;
}

.not-authenticated {
  color: #f44336;
}

.refresh-auth {
  background: rgba(255,255,255,0.2);
  border: none;
  border-radius: 3px;
  padding: 5px 8px;
  cursor: pointer;
  font-size: 12px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: white;
}

.message {
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
}

.message.user {
  align-items: flex-end;
}

.message.assistant {
  align-items: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 10px 15px;
  border-radius: 18px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #007bff;
  color: white;
}

.message.assistant .message-content {
  background: #e9ecef;
  color: #333;
}

.message-time {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
}

.loading-indicator {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 10px;
}

.input-area {
  display: flex;
  padding: 15px;
  background: white;
  border-top: 1px solid #e0e0e0;
  gap: 10px;
}

.message-input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 20px;
  outline: none;
}

.message-input:focus {
  border-color: #007bff;
}

.send-button, .logout-button {
  padding: 10px 20px;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-weight: bold;
}

.send-button {
  background: #007bff;
  color: white;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.logout-button {
  background: #dc3545;
  color: white;
}

.auth-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.auth-prompt {
  background: white;
  padding: 30px;
  border-radius: 10px;
  text-align: center;
  max-width: 300px;
}

.login-button {
  background: #28a745;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 10px;
}
</style>