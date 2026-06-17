<template>
  <div class="app-container">
    <!-- 顶部标题 -->
    <header class="header">
      <div class="header-icon">🛡️</div>
      <h1 class="header-title">反噶韭菜商品风险分析工具</h1>
      <p class="header-subtitle">
        上传商品截图或粘贴商品链接，系统将自动识别可疑宣传和消费风险
      </p>
    </header>

    <!-- ========================================== -->
    <!-- 配置面板 -->
    <!-- ========================================== -->
    <section class="config-section card">
      <div class="config-header" @click="configExpanded = !configExpanded">
        <h2 class="section-title">
          <span>⚙️ 模型配置</span>
          <span :class="configStatusClass" class="config-badge">
            {{ configBadgeText }}
          </span>
        </h2>
        <span class="config-toggle">{{ configExpanded ? '收起 ▲' : '展开 ▼' }}</span>
      </div>

      <div v-if="configExpanded" class="config-body">
        <!-- Base URL -->
        <div class="input-group">
          <label class="input-label">API Base URL</label>
          <input
            v-model="configForm.base_url"
            type="url"
            class="text-input"
            placeholder="https://api.openai.com/v1"
          />
        </div>

        <!-- API Key -->
        <div class="input-group">
          <label class="input-label">API Key</label>
          <div class="password-wrapper">
            <input
              v-model="configForm.api_key"
              :type="showApiKey ? 'text' : 'password'"
              class="text-input"
              placeholder="sk-..."
            />
            <button class="toggle-pw-btn" @click="showApiKey = !showApiKey" type="button">
              {{ showApiKey ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <!-- Model -->
        <div class="input-group">
          <label class="input-label">Model</label>
          <input
            v-model="configForm.model"
            type="text"
            class="text-input"
            placeholder="gpt-4o-mini"
          />
          <p class="input-hint">支持 gpt-4o-mini、deepseek-chat、qwen-plus 等</p>
        </div>

        <!-- Extra Prompt -->
        <div class="input-group">
          <label class="input-label">Extra Prompt（自定义额外提示词）</label>
          <textarea
            v-model="configForm.extra_prompt"
            class="text-input textarea-input"
            rows="3"
            placeholder='例如：请用更适合老年人理解的语言输出；请重点关注保健品、养生仪器、投资返利类骗局'
          ></textarea>
        </div>

        <!-- Save + Test buttons -->
        <div class="config-btn-row">
          <button class="config-save-btn" :disabled="configSaving" @click="handleSaveConfig">
            <span v-if="configSaving" class="loading-spinner-small"></span>
            <span>{{ configSaving ? '保存中...' : '💾 保存配置' }}</span>
          </button>
          <button class="config-test-btn" :disabled="configTesting" @click="handleTestApiConfig">
            <span v-if="configTesting" class="loading-spinner-small"></span>
            <span>{{ configTesting ? '测试中...' : '🧪 测试 API 配置' }}</span>
          </button>
        </div>

        <!-- Status / Test result display -->
        <div v-if="configStatusMessage" class="config-status" :class="configStatusType">
          {{ configStatusMessage }}
        </div>
      </div>
    </section>

    <!-- ========================================== -->
    <!-- 输入区域 -->
    <!-- ========================================== -->
    <section class="input-section card">
      <h2 class="section-title">输入商品信息</h2>

      <!-- 图片上传 -->
      <div class="input-group">
        <label class="input-label">上传商品截图</label>
        <div
          class="upload-zone"
          :class="{ 'upload-zone--active': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            hidden
            @change="handleFileSelect"
          />
          <template v-if="selectedImage">
            <div class="upload-preview">
              <img :src="imagePreviewUrl" alt="预览" class="preview-img" />
              <button class="upload-remove" @click.stop="removeImage">✕</button>
            </div>
            <p class="upload-hint">{{ selectedImage.name }}</p>
          </template>
          <template v-else>
            <div class="upload-icon">📁</div>
            <p class="upload-text">点击或拖拽上传商品截图</p>
            <p class="upload-hint">支持 JPG、PNG、WebP 格式</p>
          </template>
        </div>
      </div>

      <!-- 分割线 -->
      <div class="divider">
        <span class="divider-text">或者</span>
      </div>

      <!-- URL 输入 -->
      <div class="input-group">
        <label class="input-label">粘贴商品链接</label>
        <div class="url-input-wrapper">
          <input
            v-model="url"
            type="url"
            class="text-input url-input"
            placeholder="https://example.com/product/123"
            @input="handleUrlInput"
          />
          <button
            v-if="url"
            class="url-clear"
            @click="url = ''"
            title="清除"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- 分析按钮 -->
      <button
        class="analyze-btn"
        :disabled="!canAnalyze || loading"
        @click="startAnalysis"
      >
        <span v-if="loading" class="loading-spinner"></span>
        <span>{{ loading ? '分析中...' : '🔍 开始分析' }}</span>
      </button>
    </section>

    <!-- 错误提示 -->
    <div v-if="error" class="error-banner card">
      <span class="error-icon">❌</span>
      <span>{{ error }}</span>
    </div>

    <!-- ========================================== -->
    <!-- 报告展示 -->
    <!-- ========================================== -->
    <section v-if="report" class="report-section">
      <!-- 当前模式 & 风险等级 -->
      <div class="mode-banner" :class="modeBannerClass">
        <span class="mode-badge">{{ modeLabel }}</span>
      </div>

      <div class="risk-banner" :class="riskBannerClass">
        <div class="risk-level">
          <span class="risk-icon">{{ riskIcon }}</span>
          <span class="risk-text">风险等级：{{ report.risk_level }}</span>
        </div>
        <p class="risk-summary">{{ report.summary }}</p>
      </div>

      <!-- 可疑宣传语 -->
      <div class="card report-card">
        <h3 class="report-card-title">
          <span class="report-card-icon">🚩</span>
          可疑宣传语
        </h3>
        <ul class="report-list">
          <li
            v-for="(claim, index) in report.suspicious_claims"
            :key="index"
            class="report-list-item"
          >
            {{ claim }}
          </li>
        </ul>
      </div>

      <!-- 营销套路 -->
      <div class="card report-card">
        <h3 class="report-card-title">
          <span class="report-card-icon">🎭</span>
          可能使用的营销套路
        </h3>
        <ul class="report-list">
          <li
            v-for="(trick, index) in report.marketing_tricks"
            :key="index"
            class="report-list-item"
          >
            {{ trick }}
          </li>
        </ul>
      </div>

      <!-- 事实核查建议 -->
      <div class="card report-card">
        <h3 class="report-card-title">
          <span class="report-card-icon">🔎</span>
          事实核查建议
        </h3>
        <ul class="report-list">
          <li
            v-for="(suggestion, index) in report.fact_check_suggestions"
            :key="index"
            class="report-list-item"
          >
            {{ suggestion }}
          </li>
        </ul>
      </div>

      <!-- 购买建议 -->
      <div class="card report-card">
        <h3 class="report-card-title">
          <span class="report-card-icon">💡</span>
          购买建议
        </h3>
        <p class="report-text">{{ report.purchase_advice }}</p>
      </div>

      <!-- 中老年用户提醒 -->
      <div class="card report-card report-card--warning">
        <h3 class="report-card-title">
          <span class="report-card-icon">👴</span>
          给中老年用户的简明提醒
        </h3>
        <p class="report-text report-text--warning">
          {{ report.elderly_friendly_warning }}
        </p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { analyzeProduct, saveConfig, getConfigStatus, testApiConfig } from './api.js'

// =====================================================
// 状态：分析流程
// =====================================================
const fileInput = ref(null)
const selectedImage = ref(null)
const imagePreviewUrl = ref('')
const url = ref('')
const loading = ref(false)
const error = ref('')
const report = ref(null)
const analysisMode = ref(null) // 'real_api' | 'mock'

// =====================================================
// 状态：配置面板
// =====================================================
const configExpanded = ref(false)
const configSaving = ref(false)
const configTesting = ref(false)
const configStatusMessage = ref('')
const configStatusType = ref('success')
const showApiKey = ref(false)

const configForm = ref({
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  model: 'gpt-4o-mini',
  extra_prompt: '',
})

// 从后端获取的配置状态
const configStatus = ref({
  api_configured: false,
  base_url: '',
  model: '',
  extra_prompt_configured: false,
  mode: 'mock',
})

// =====================================================
// 生命周期
// =====================================================
onMounted(async () => {
  try {
    const status = await getConfigStatus()
    configStatus.value = status
    configForm.value.base_url = status.base_url || 'https://api.openai.com/v1'
    configForm.value.model = status.model || 'gpt-4o-mini'
  } catch (e) {
    // 后端未启动时静默处理
  }
})

// =====================================================
// 计算属性
// =====================================================
const canAnalyze = computed(() => {
  return selectedImage.value || url.value.trim()
})

const isDragOver = ref(false)

const configStatusClass = computed(() => {
  return configStatus.value.api_configured ? 'badge--online' : 'badge--offline'
})

const configBadgeText = computed(() => {
  return configStatus.value.api_configured ? '已配置 API' : 'Mock 演示模式'
})

const modeLabel = computed(() => {
  return analysisMode.value === 'real_api' ? '✅ 当前结果来自真实 API' : '⚠️ 当前结果来自 Mock 演示模式'
})

const modeBannerClass = computed(() => {
  return analysisMode.value === 'real_api' ? 'mode-banner--real' : 'mode-banner--mock'
})

const riskBannerClass = computed(() => {
  if (!report.value) return ''
  const level = report.value.risk_level
  if (level === '高') return 'risk-banner--high'
  if (level === '中') return 'risk-banner--medium'
  return 'risk-banner--low'
})

const riskIcon = computed(() => {
  if (!report.value) return ''
  const level = report.value.risk_level
  if (level === '高') return '🔴'
  if (level === '中') return '🟡'
  return '🟢'
})

// =====================================================
// 方法：配置
// =====================================================
async function handleTestApiConfig() {
  configTesting.value = true
  configStatusMessage.value = ''

  try {
    const result = await testApiConfig()
    if (result.success) {
      configStatusMessage.value = `✅ API 配置可用（模型：${result.model}）`
      configStatusType.value = 'success'
    } else {
      configStatusMessage.value = `❌ ${result.message}`
      configStatusType.value = 'error'
    }
  } catch (err) {
    configStatusMessage.value = '❌ 测试请求失败：' + (err.response?.data?.detail || err.message)
    configStatusType.value = 'error'
  } finally {
    configTesting.value = false
  }
}

async function handleSaveConfig() {
  configSaving.value = true
  configStatusMessage.value = ''

  try {
    const result = await saveConfig({
      base_url: configForm.value.base_url,
      api_key: configForm.value.api_key,
      model: configForm.value.model,
      extra_prompt: configForm.value.extra_prompt,
    })

    if (result.success) {
      configStatusMessage.value = '配置已保存！'
      configStatusType.value = 'success'

      // 刷新配置状态
      const status = await getConfigStatus()
      configStatus.value = status
    } else {
      configStatusMessage.value = '保存失败，请重试'
      configStatusType.value = 'error'
    }
  } catch (err) {
    configStatusMessage.value = '保存失败：' + (err.response?.data?.detail || err.message)
    configStatusType.value = 'error'
  } finally {
    configSaving.value = false
  }
}

// =====================================================
// 方法：图片上传
// =====================================================
function triggerFileInput() {
  if (!selectedImage.value) {
    fileInput.value.click()
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    setImage(file)
  }
}

function handleDrop(event) {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) {
    setImage(file)
  }
}

function setImage(file) {
  selectedImage.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreviewUrl.value = e.target.result
  }
  reader.readAsDataURL(file)
}

function removeImage() {
  selectedImage.value = null
  imagePreviewUrl.value = ''
}

// =====================================================
// 方法：URL 输入 & 分析
// =====================================================
function handleUrlInput() {
  if (error.value) {
    error.value = ''
  }
}

async function startAnalysis() {
  error.value = ''
  report.value = null
  analysisMode.value = null

  if (!canAnalyze.value) {
    error.value = '请上传商品截图或输入商品链接'
    return
  }

  loading.value = true

  try {
    const result = await analyzeProduct(selectedImage.value, url.value.trim() || null)

    if (result.success) {
      report.value = result.report
      analysisMode.value = result.mode
    } else {
      error.value = '分析失败，请稍后重试'
    }
  } catch (err) {
    if (err.response) {
      error.value = `请求失败：${err.response.data?.detail || err.response.statusText}`
    } else if (err.request) {
      error.value = '无法连接到后端服务，请确保后端已启动'
    } else {
      error.value = `发生错误：${err.message}`
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ============================================================
   页面容器
   ============================================================ */

.app-container {
  max-width: 100%;
}

/* ============================================================
   头部
   ============================================================ */

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.header-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.header-subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.5;
}

/* ============================================================
   配置面板
   ============================================================ */

.config-section {
  margin-bottom: 20px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.config-header .section-title {
  margin-bottom: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-toggle {
  font-size: 13px;
  color: var(--color-primary);
  white-space: nowrap;
}

.config-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.badge--online {
  background: #e6f4ea;
  color: #188038;
}

.badge--offline {
  background: #fef7e0;
  color: #e37400;
}

.config-body {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.config-body .input-group {
  margin-bottom: 12px;
}

.password-wrapper {
  position: relative;
}

.toggle-pw-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  font-size: 16px;
  padding: 4px;
  border-radius: 4px;
}

.toggle-pw-btn:hover {
  background: #f1f3f4;
}

.input-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.config-save-btn {
  width: 100%;
  padding: 10px 20px;
  background: #34a853;
  color: white;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 4px;
}

.config-save-btn:hover:not(:disabled) {
  background: #2d9249;
}

.config-btn-row {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.config-btn-row .config-save-btn,
.config-btn-row .config-test-btn {
  flex: 1;
}

.config-test-btn {
  padding: 10px 20px;
  background: #1a73e8;
  color: white;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 4px;
}

.config-test-btn:hover:not(:disabled) {
  background: #1557b0;
}

.config-status {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.config-status.success {
  background: #e6f4ea;
  color: #188038;
}

.config-status.error {
  background: #fce8e6;
  color: #d93025;
}

.loading-spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* ============================================================
   输入区域
   ============================================================ */

.input-section {
  /* 继承 .card 样式 */
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--color-text);
}

.input-group {
  margin-bottom: 16px;
}

.input-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.text-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  font-size: 15px;
  color: var(--color-text);
  background: white;
  transition: border-color 0.2s;
  outline: none;
}

.text-input:focus {
  border-color: var(--color-primary);
}

.text-input::placeholder {
  color: #9aa0a6;
}

.textarea-input {
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
  line-height: 1.5;
}

/* 上传区域 */
.upload-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.upload-zone:hover {
  border-color: var(--color-primary);
  background: #e8f0fe;
}

.upload-zone--active {
  border-color: var(--color-primary);
  background: #e8f0fe;
}

.upload-icon {
  font-size: 36px;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 15px;
  color: var(--color-text);
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 上传预览 */
.upload-preview {
  position: relative;
  display: inline-block;
  max-width: 200px;
  margin-bottom: 8px;
}

.preview-img {
  width: 100%;
  max-height: 150px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.upload-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-danger);
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.upload-remove:hover {
  background: #b3261e;
}

/* 分割线 */
.divider {
  display: flex;
  align-items: center;
  margin: 20px 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.divider-text {
  padding: 0 16px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* URL 输入 */
.url-input-wrapper {
  position: relative;
}

.url-input {
  padding-right: 40px;
}

.url-clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.url-clear:hover {
  background: #f1f3f4;
}

/* 分析按钮 */
.analyze-btn {
  width: 100%;
  padding: 14px 24px;
  background: var(--color-primary);
  color: white;
  border-radius: 8px;
  font-size: 17px;
  font-weight: 600;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analyze-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
}

/* Loading 动画 */
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ============================================================
   错误提示
   ============================================================ */

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fce8e6;
  border: 1px solid #f5c6cb;
  color: var(--color-danger);
  font-size: 14px;
}

.error-icon {
  font-size: 18px;
}

/* ============================================================
   报告区域
   ============================================================ */

.report-section {
  margin-top: 24px;
}

/* 模式横幅 */
.mode-banner {
  border-radius: var(--radius);
  padding: 10px 16px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}

.mode-banner--real {
  background: #e6f4ea;
  border: 1px solid #c3e6cb;
  color: #188038;
}

.mode-banner--mock {
  background: #fef7e0;
  border: 1px solid #ffeeba;
  color: #e37400;
}

.mode-badge {
  display: inline-block;
}

/* 风险等级横幅 */
.risk-banner {
  border-radius: var(--radius);
  padding: 20px 24px;
  margin-bottom: 20px;
}

.risk-banner--high {
  background: linear-gradient(135deg, #fce8e6, #f8d7da);
  border: 1px solid #f5c6cb;
}

.risk-banner--medium {
  background: linear-gradient(135deg, #fef7e0, #fff3cd);
  border: 1px solid #ffeeba;
}

.risk-banner--low {
  background: linear-gradient(135deg, #e6f4ea, #d4edda);
  border: 1px solid #c3e6cb;
}

.risk-level {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.risk-icon {
  font-size: 24px;
}

.risk-text {
  font-size: 20px;
  font-weight: 700;
}

.risk-banner--high .risk-text {
  color: #c62828;
}

.risk-banner--medium .risk-text {
  color: #e37400;
}

.risk-banner--low .risk-text {
  color: #188038;
}

.risk-summary {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text);
}

/* 报告卡片 */
.report-card {
  /* 继承 .card 样式 */
}

.report-card-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-card-icon {
  font-size: 20px;
}

.report-list {
  list-style: none;
  padding: 0;
}

.report-list-item {
  position: relative;
  padding: 8px 0 8px 20px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text);
  border-bottom: 1px solid #f1f3f4;
}

.report-list-item:last-child {
  border-bottom: none;
}

.report-list-item::before {
  content: '•';
  position: absolute;
  left: 4px;
  color: var(--color-primary);
  font-weight: bold;
}

.report-text {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text);
}

.report-card--warning {
  background: #fff8e1;
  border: 1px solid #ffecb3;
}

.report-text--warning {
  font-size: 15px;
  line-height: 1.7;
  color: #e65100;
}

/* 响应式 */
@media (max-width: 640px) {
  .header-title {
    font-size: 22px;
  }

  .header-subtitle {
    font-size: 14px;
  }

  .upload-zone {
    padding: 20px;
  }

  .risk-text {
    font-size: 18px;
  }
}
</style>