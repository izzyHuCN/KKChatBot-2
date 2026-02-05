<template>
  <div class="dashboard-container">
    <div class="header">
      <h1>学习数据追踪与智能分析</h1>
      <el-button @click="$router.push('/')">返回聊天</el-button>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <el-card class="stat-card">
        <template #header>
          <div class="card-header">
            <span>总登录次数</span>
          </div>
        </template>
        <div class="stat-value">{{ stats.total_logins }}</div>
      </el-card>

      <el-card class="stat-card">
        <template #header>
          <div class="card-header">
            <span>提问总数</span>
          </div>
        </template>
        <div class="stat-value">{{ stats.questions_asked }}</div>
      </el-card>

      <el-card class="stat-card">
        <template #header>
          <div class="card-header">
            <span>平均测验分</span>
          </div>
        </template>
        <div class="stat-value">{{ stats.quiz_average }}</div>
      </el-card>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- AI Analysis -->
      <el-card class="analysis-card">
        <template #header>
          <div class="card-header">
            <span>AI 智能学习画像</span>
            <el-button type="primary" size="small" :loading="analyzing" @click="generateAnalysis">
              生成/更新分析
            </el-button>
          </div>
        </template>
        <div class="analysis-body" v-loading="analyzing">
          <div v-if="stats.ai_analysis" v-html="renderMarkdown(stats.ai_analysis)" class="markdown-body"></div>
          <div v-else class="empty-state">暂无分析数据，请点击右上角按钮生成。</div>
        </div>
      </el-card>

      <!-- Recent Activity -->
      <el-card class="activity-card">
        <template #header>
          <div class="card-header">
            <span>最近学习活动</span>
          </div>
        </template>
        <el-table :data="stats.recent_activity" style="width: 100%">
          <el-table-column prop="date" label="时间" width="160" />
          <el-table-column prop="type" label="类型" width="100">
             <template #default="scope">
                <el-tag :type="getEventTypeTag(scope.row.type)">{{ formatEventType(scope.row.type) }}</el-tag>
             </template>
          </el-table-column>
          <el-table-column prop="content" label="详情" />
          <el-table-column prop="score" label="分数" width="80" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'
import { marked } from 'marked'

const stats = ref({
  total_logins: 0,
  questions_asked: 0,
  quiz_average: 0,
  recent_activity: [],
  ai_analysis: ''
})

const analyzing = ref(false)

const loadData = async () => {
  try {
    const res = await api.getDashboardData()
    stats.value = res
  } catch (e) {
    console.error(e)
  }
}

const generateAnalysis = async () => {
  analyzing.value = true
  try {
    const res = await api.analyzeLearning()
    stats.value.ai_analysis = res.analysis
    // Reload activity to show the new analysis event
    loadData()
  } catch (e) {
    console.error(e)
  } finally {
    analyzing.value = false
  }
}

const renderMarkdown = (text) => {
  return marked(text || '')
}

const formatEventType = (type) => {
    const map = {
        'login': '登录',
        'quiz_result': '测验',
        'question_asked': '提问',
        'ai_analysis': 'AI分析',
        'page_view': '浏览'
    }
    return map[type] || type
}

const getEventTypeTag = (type) => {
    const map = {
        'login': 'info',
        'quiz_result': 'danger',
        'question_asked': 'success',
        'ai_analysis': 'warning'
    }
    return map[type] || ''
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.stats-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}
.main-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.analysis-body {
  min-height: 200px;
  line-height: 1.6;
}
.markdown-body :deep(h1), .markdown-body :deep(h2) {
    font-size: 1.2em;
    margin-top: 10px;
    margin-bottom: 10px;
    color: #333;
}
.markdown-body :deep(ul) {
    padding-left: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
