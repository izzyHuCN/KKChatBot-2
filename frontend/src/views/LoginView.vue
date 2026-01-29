<template>
  <div class="login-container">
    <div class="login-card">
      <div class="logo-area">
        <img src="https://img.icons8.com/color/96/robot-2.png" alt="Logo" class="logo" />
        <h1>KKChatBot-2</h1>
      </div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="admin" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="123456" required />
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
const username = ref('admin');
const password = ref('123456');
const loading = ref(false);

const handleLogin = async () => {
  loading.value = true;
  try {
    console.log("Sending login request...", { username: username.value, password: password.value });
    const response = await api.login({
      username: username.value,
      password: password.value
    });
    console.log("Login successful:", response);
    localStorage.setItem('access_token', response.access_token);
    router.push('/');
  } catch (error) {
    console.error("Login failed error object:", error);
    let errorMessage = "登录失败";
    
    if (error.response) {
       console.error("Error response data:", error.response.data);
       if (error.response.data && error.response.data.detail) {
         // detail could be an array (validation error) or string
         if (Array.isArray(error.response.data.detail)) {
            errorMessage += ": " + error.response.data.detail.map(e => e.msg).join(", ");
         } else {
            errorMessage += ": " + error.response.data.detail;
         }
       }
    } else if (error.message) {
       errorMessage += ": " + error.message;
    }
    
    alert(errorMessage);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.login-card {
  background: white;
  padding: 40px;
  border-radius: 20px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
}

.logo-area {
  text-align: center;
  margin-bottom: 30px;
}

.logo {
  width: 80px;
  height: 80px;
  margin-bottom: 15px;
}

h1 {
  font-size: 1.8rem;
  color: #333;
  margin: 0;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #666;
  font-size: 0.9rem;
}

input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  outline: none;
  transition: border-color 0.3s;
}

input:focus {
  border-color: #FFB7B2;
}

button {
  width: 100%;
  padding: 12px;
  background: #FFB7B2;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.3s;
}

button:hover {
  opacity: 0.9;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
