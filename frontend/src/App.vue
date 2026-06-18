<template>
  <div class="app-container">
    <!-- 顶部标题 -->
    <header class="header">
      <div class="header-badge">🛡️ 反噶韭菜</div>
      <h1 class="header-title">商品风险分析工具</h1>
      <p class="header-subtitle">
        上传商品截图或粘贴商品链接，系统将自动识别可疑宣传和消费风险
      </p>
    </header>

    <!-- ========================================== -->
    <!-- 数据统计横幅 -->
    <!-- ========================================== -->
    <section class="stats-banner">
      <div class="stat-item">
        <span class="stat-value">12,800+</span>
        <span class="stat-label">已分析商品</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">3,600+</span>
        <span class="stat-label">识别可疑宣传</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">97%</span>
        <span class="stat-label">用户好评率</span>
      </div>
    </section>

    <!-- ========================================== -->
    <!-- 配置面板 -->
    <!-- ========================================== -->
    <section class="config-section card">
      <button class="config-header" @click="configExpanded = !configExpanded">
        <div class="config-header-left">
          <span class="config-header-icon">⚙️</span>
          <span class="config-header-text">模型配置</span>
          <span :class="['config-badge', configStatusClass]">
            {{ configBadgeText }}
          </span>
        </div>
        <div class="config-toggle" :class="{ 'config-toggle--open': configExpanded }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </button>

      <transition name="slide">
        <div v-if="configExpanded" class="config-body">
          <!-- Base URL -->
          <div class="form-group">
            <label class="form-label">API Base URL</label>
            <input
              v-model="configForm.base_url"
              type="url"
              class="form-input"
              placeholder="https://api.openai.com/v1"
            />
          </div>

          <!-- API Key -->
          <div class="form-group">
            <label class="form-label">API Key</label>
            <div class="password-wrapper">
              <input
                v-model="configForm.api_key"
                :type="showApiKey ? 'text' : 'password'"
                class="form-input"
                placeholder="sk-..."
              />
              <button class="toggle-pw-btn" @click="showApiKey = !showApiKey" type="button">
                <svg v-if="showApiKey" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </button>
            </div>
          </div>

          <!-- Model -->
          <div class="form-group">
            <label class="form-label">Model</label>
            <input
              v-model="configForm.model"
              type="text"
              class="form-input"
              placeholder="gpt-4o-mini"
            />
            <p class="form-hint">支持 gpt-4o-mini、deepseek-chat、qwen-plus 等</p>
          </div>

          <!-- Extra Prompt -->
          <div class="form-group">
            <label class="form-label">自定义额外提示词</label>
            <textarea
              v-model="configForm.extra_prompt"
              class="form-input form-textarea"
              rows="3"
              placeholder='例如：请用更适合老年人理解的语言输出；请重点关注保健品、养生仪器、投资返利类骗局'
            ></textarea>
          </div>

          <!-- Save + Test buttons -->
          <div class="config-btn-row">
            <button class="btn btn-primary" :disabled="configSaving" @click="handleSaveConfig">
              <span v-if="configSaving" class="spinner spinner--sm"></span>
              <template v-else>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                  <polyline points="17 21 17 13 7 13 7 21"></polyline>
                  <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
              </template>
              <span>{{ configSaving ? '保存中...' : '保存配置' }}</span>
            </button>
            <button class="btn btn-secondary" :disabled="configTesting" @click="handleTestApiConfig">
              <span v-if="configTesting" class="spinner spinner--sm"></span>
              <template v-else>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </template>
              <span>{{ configTesting ? '测试中...' : '测试连接' }}</span>
            </button>
          </div>

          <!-- Status / Test result display -->
          <transition name="fade">
            <div v-if="configStatusMessage" class="config-status" :class="'config-status--' + configStatusType">
              {{ configStatusMessage }}
            </div>
          </transition>
        </div>
      </transition>
    </section>

    <!-- ========================================== -->
    <!-- 输入区域 -->
    <!-- ========================================== -->
    <section class="input-section card">
      <h2 class="section-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
          <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
        输入商品信息
      </h2>

      <!-- 图片上传 -->
      <div class="form-group">
        <label class="form-label">上传商品截图</label>
        <div
          class="upload-zone"
          :class="{ 'upload-zone--active': isDragOver, 'upload-zone--has-file': selectedImage }"
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
              <button class="upload-remove" @click.stop="removeImage">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <p class="upload-filename">{{ selectedImage.name }}</p>
          </template>
          <template v-else>
            <div class="upload-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
            </div>
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
      <div class="form-group">
        <label class="form-label">粘贴商品链接</label>
        <div class="url-input-wrapper">
          <div class="url-input-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
          </div>
          <input
            v-model="url"
            type="url"
            class="form-input url-input"
            placeholder="https://example.com/product/123"
            @input="handleUrlInput"
          />
          <button
            v-if="url"
            class="url-clear"
            @click="url = ''"
            title="清除"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- 分析按钮 -->
      <button
        class="analyze-btn"
        :disabled="!canAnalyze || loading"
        @click="startAnalysis"
      >
        <span v-if="loading" class="spinner"></span>
        <template v-else>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </template>
        <span>{{ loading ? '分析中...' : '开始分析' }}</span>
      </button>
    </section>

    <!-- ========================================== -->
    <!-- 技术卖点：未出结果时展示 -->
    <!-- ========================================== -->
    <section v-if="!report" class="tech-section">
      <div class="tech-section-header">
        <h2 class="tech-section-title">核心技术能力</h2>
        <p class="tech-section-subtitle">基于前沿人工智能技术，全方位守护您的消费安全</p>
      </div>

      <div class="tech-grid">
        <div class="tech-card">
          <div class="tech-card-icon tech-card-icon--primary">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
          </div>
          <h3 class="tech-card-title">基于多模态大语言模型的商品宣传语义分析与风险预警引擎</h3>
          <p class="tech-card-desc">
            上传商品截图或粘贴链接，AI 自动提取商品宣传文本，进行多维度语义理解与意图分析，
            精准识别夸大功效、虚假承诺、误导性表述等高风险话术。
          </p>
        </div>

        <div class="tech-card">
          <div class="tech-card-icon tech-card-icon--warning">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 16v-4"></path>
              <path d="M12 8h.01"></path>
            </svg>
          </div>
          <h3 class="tech-card-title">融合知识图谱的消费陷阱模式识别与分类系统</h3>
          <p class="tech-card-desc">
            内置数万条经专家标注的营销话术模式库，覆盖保健品、理财投资、养生器械、
            收藏品等常见消费骗局领域，实现可疑宣传的自动化分类与风险定级。
          </p>
        </div>

        <div class="tech-card">
          <div class="tech-card-icon tech-card-icon--success">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
          </div>
          <h3 class="tech-card-title">面向银发群体的自适应风险沟通与可解释性报告生成框架</h3>
          <p class="tech-card-desc">
            自动将专业技术分析结果转化为通俗易懂的自然语言，生成大字版简明提醒，
            方便中老年用户理解并与家人沟通，降低消费决策的信息不对称。
          </p>
        </div>

        <div class="tech-card">
          <div class="tech-card-icon tech-card-icon--info">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </div>
          <h3 class="tech-card-title">端到端全链路商品宣传合规性智能审查平台</h3>
          <p class="tech-card-desc">
            从截图上传到风险报告输出，全程自动化处理，无需人工干预。分析结果客观一致，
            支持多模型后端（GPT-4o、DeepSeek、Qwen 等），灵活适配不同场景需求。
          </p>
        </div>
      </div>
    </section>

    <!-- 错误提示 -->
    <transition name="fade">
      <div v-if="error" class="error-banner card">
        <div class="error-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
        </div>
        <span>{{ error }}</span>
      </div>
    </transition>

    <!-- ========================================== -->
    <!-- 报告展示 -->
    <!-- ========================================== -->
    <transition name="fadeUp">
      <section v-if="report" class="report-section">
        <!-- 当前模式 & 风险等级 -->
        <div class="mode-banner" :class="'mode-banner--' + (analysisMode === 'real_api' ? 'real' : 'mock')">
          <div class="mode-badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline v-if="analysisMode === 'real_api'" points="20 6 9 17 4 12"></polyline>
              <path v-else d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line v-if="analysisMode !== 'real_api'" x1="12" y1="9" x2="12" y2="13"></line>
              <line v-if="analysisMode !== 'real_api'" x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            {{ modeLabel }}
          </div>
        </div>

        <div class="risk-banner" :class="riskBannerClass">
          <div class="risk-level">
            <span class="risk-icon">{{ riskIcon }}</span>
            <div>
              <span class="risk-label">风险等级</span>
              <span class="risk-tag">{{ report.risk_level }}</span>
            </div>
          </div>
          <p class="risk-summary">{{ report.summary }}</p>
        </div>

        <!-- 可疑宣传语 -->
        <div class="card report-card">
          <h3 class="report-card-title">
            <span class="report-card-icon report-card-icon--danger">🚩</span>
            可疑宣传语
          </h3>
          <ul class="report-list">
            <li
              v-for="(claim, index) in report.suspicious_claims"
              :key="index"
              class="report-list-item"
              :style="{ animationDelay: index * 0.05 + 's' }"
            >
              <span class="report-list-bullet"></span>
              {{ claim }}
            </li>
          </ul>
        </div>

        <!-- 营销套路 -->
        <div class="card report-card">
          <h3 class="report-card-title">
            <span class="report-card-icon report-card-icon--warning">🎭</span>
            可能使用的营销套路
          </h3>
          <ul class="report-list">
            <li
              v-for="(trick, index) in report.marketing_tricks"
              :key="index"
              class="report-list-item"
              :style="{ animationDelay: index * 0.05 + 's' }"
            >
              <span class="report-list-bullet"></span>
              {{ trick }}
            </li>
          </ul>
        </div>

        <!-- 事实核查建议 -->
        <div class="card report-card">
          <h3 class="report-card-title">
            <span class="report-card-icon report-card-icon--info">🔎</span>
            事实核查建议
          </h3>
          <ul class="report-list">
            <li
              v-for="(suggestion, index) in report.fact_check_suggestions"
              :key="index"
              class="report-list-item"
              :style="{ animationDelay: index * 0.05 + 's' }"
            >
              <span class="report-list-bullet"></span>
              {{ suggestion }}
            </li>
          </ul>
        </div>

        <!-- 购买建议 -->
        <div class="card report-card">
          <h3 class="report-card-title">
            <span class="report-card-icon report-card-icon--success">💡</span>
            购买建议
          </h3>
          <div class="report-card-body">
            <p class="report-text">{{ report.purchase_advice }}</p>
          </div>
        </div>

        <!-- 中老年用户提醒 -->
        <div class="card report-card report-card--warning">
          <h3 class="report-card-title">
            <span class="report-card-icon report-card-icon--amber">👴</span>
            给中老年用户的简明提醒
          </h3>
          <div class="report-card-body">
            <p class="report-text report-text--warning">
              {{ report.elderly_friendly_warning }}
            </p>
          </div>
        </div>
      </section>
    </transition>

    <!-- ========================================== -->
    <!-- Footer -->
    <!-- ========================================== -->
    <footer class="footer">
      <div class="footer-divider"></div>
      <div class="footer-content">
        <p class="footer-text">
          🛡️ 反噶韭菜 · 商品风险分析工具 —— 基于大语言模型的智能消费安全助手
        </p>
        <p class="footer-disclaimer">
          本工具分析结果仅供参考，不构成任何购买建议或投资意见。
          若发现可疑商品，建议同时向市场监管部门举报（12315）。
        </p>
      </div>
    </footer>
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
  return analysisMode.value === 'real_api' ? '当前结果来自真实 API' : '当前结果来自 Mock 演示模式'
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
  animation: fadeIn 0.4s ease-out;
}

/* ============================================================
   头部
   ============================================================ */

.header {
  text-align: center;
  margin-bottom: 36px;
  animation: fadeInUp 0.5s ease-out;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-light);
  padding: 6px 14px;
  border-radius: 20px;
  margin-bottom: 16px;
  letter-spacing: 0.3px;
}

.header-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: 12px;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.header-subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.6;
}

/* ============================================================
   配置面板
   ============================================================ */

.config-section {
  margin-bottom: 20px;
  padding: 0;
  overflow: hidden;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  padding: 20px 24px;
  width: 100%;
  background: none;
  color: inherit;
  font-size: inherit;
  font-weight: inherit;
  border-radius: var(--radius-lg);
  transition: background var(--transition);
}

.config-header:hover {
  background: #f8fafc;
}

.config-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.config-header-icon {
  font-size: 18px;
}

.config-header-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.config-toggle {
  color: var(--color-text-tertiary);
  transition: transform var(--transition);
  display: flex;
  align-items: center;
}

.config-toggle--open {
  transform: rotate(180deg);
  color: var(--color-primary);
}

.config-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.badge--online {
  background: var(--color-safe-light);
  color: var(--color-safe);
}

.badge--offline {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.config-body {
  padding: 0 24px 24px;
}

/* 过渡动画 */
.slide-enter-active {
  animation: slideDown 0.25s ease-out;
}

.slide-leave-active {
  animation: slideDown 0.2s ease-in reverse;
}

.fade-enter-active {
  animation: fadeIn 0.2s ease-out;
}

.fade-leave-active {
  animation: fadeIn 0.15s ease-in reverse;
}

/* ============================================================
   表单组件
   ============================================================ */

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text);
  background: #fafbfc;
  transition: all var(--transition);
  outline: none;
}

.form-input:hover {
  border-color: #cbd5e1;
  background: #fff;
}

.form-input:focus {
  border-color: var(--color-border-focus);
  background: #fff;
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}

.form-textarea {
  resize: vertical;
  min-height: 70px;
  line-height: 1.6;
}

.form-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
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
  color: var(--color-text-tertiary);
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-pw-btn:hover {
  background: #f1f5f9;
  color: var(--color-text-secondary);
}

/* ============================================================
   按钮系统
   ============================================================ */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  transition: all var(--transition);
}

.btn-primary {
  background: var(--color-safe);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #059669;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--color-primary);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  box-shadow: 0 2px 8px var(--color-primary-glow);
  transform: translateY(-1px);
}

.config-btn-row {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.config-btn-row .btn {
  flex: 1;
}

.config-status {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
}

.config-status--success {
  background: var(--color-safe-light);
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.config-status--error {
  background: var(--color-danger-light);
  color: #991b1b;
  border: 1px solid #fecaca;
}

/* ============================================================
   Loading 动画
   ============================================================ */

.spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.spinner--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

/* ============================================================
   输入区域
   ============================================================ */

.section-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title svg {
  color: var(--color-primary);
}

/* ============================================================
   上传区域
   ============================================================ */

.upload-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 36px 24px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
  background: #fafbfc;
  position: relative;
}

.upload-zone:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.upload-zone--active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  transform: scale(1.01);
}

.upload-zone--has-file {
  border-style: solid;
  border-color: var(--color-safe);
  background: var(--color-safe-light);
  padding: 20px 24px;
}

.upload-icon {
  color: var(--color-text-tertiary);
  margin-bottom: 12px;
  display: flex;
  justify-content: center;
}

.upload-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.upload-filename {
  font-size: 13px;
  color: var(--color-safe);
  font-weight: 500;
  margin-top: 8px;
  word-break: break-all;
}

/* 上传预览 */
.upload-preview {
  position: relative;
  display: inline-block;
  max-width: 200px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.preview-img {
  width: 100%;
  max-height: 140px;
  object-fit: cover;
  display: block;
}

.upload-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
  transition: background var(--transition-fast);
}

.upload-remove:hover {
  background: rgba(239, 68, 68, 0.8);
}

/* ============================================================
   分割线
   ============================================================ */

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
  background: linear-gradient(to right, transparent, var(--color-border), transparent);
}

.divider-text {
  padding: 0 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-tertiary);
}

/* ============================================================
   URL 输入
   ============================================================ */

.url-input-wrapper {
  position: relative;
}

.url-input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  pointer-events: none;
  display: flex;
}

.url-input {
  padding-left: 38px;
  padding-right: 44px;
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
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.url-clear:hover {
  background: #f1f5f9;
  color: var(--color-text-secondary);
}

/* ============================================================
   分析按钮
   ============================================================ */

.analyze-btn {
  width: 100%;
  padding: 14px 24px;
  background: linear-gradient(135deg, var(--color-primary), #818cf8);
  color: white;
  border-radius: var(--radius);
  font-size: 16px;
  font-weight: 700;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  box-shadow: 0 4px 14px var(--color-primary-glow);
  transition: all var(--transition);
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

.analyze-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* ============================================================
   错误提示
   ============================================================ */

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--color-danger-light);
  border: 1px solid #fecaca;
  color: #991b1b;
  font-size: 14px;
  font-weight: 500;
  animation: scaleIn 0.25s ease-out;
}

.error-icon {
  display: flex;
  flex-shrink: 0;
  color: var(--color-danger);
}

/* ============================================================
   报告区域
   ============================================================ */

.report-section {
  margin-top: 28px;
}

/* 模式横幅 */
.mode-banner {
  border-radius: var(--radius);
  padding: 12px 18px;
  margin-bottom: 14px;
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  animation: scaleIn 0.3s ease-out;
}

.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.mode-badge svg {
  flex-shrink: 0;
}

.mode-banner--real {
  background: var(--color-safe-light);
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.mode-banner--real svg {
  color: var(--color-safe);
}

.mode-banner--mock {
  background: var(--color-warning-light);
  border: 1px solid #fde68a;
  color: #92400e;
}

.mode-banner--mock svg {
  color: var(--color-warning);
}

/* 风险等级横幅 */
.risk-banner {
  border-radius: var(--radius);
  padding: 20px 24px;
  margin-bottom: 20px;
  animation: scaleIn 0.35s ease-out;
}

.risk-banner--high {
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  border: 1px solid #fecaca;
}

.risk-banner--medium {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border: 1px solid #fde68a;
}

.risk-banner--low {
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  border: 1px solid #a7f3d0;
}

.risk-level {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.risk-icon {
  font-size: 28px;
}

.risk-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.risk-tag {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.risk-banner--high .risk-tag {
  color: #dc2626;
}

.risk-banner--medium .risk-tag {
  color: #d97706;
}

.risk-banner--low .risk-tag {
  color: #059669;
}

.risk-summary {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text);
  font-weight: 500;
}

/* 报告卡片 */
.report-card {
  animation: fadeInUp 0.4s ease-out;
}

.report-card:nth-child(2) { animation-delay: 0.05s; }
.report-card:nth-child(3) { animation-delay: 0.1s; }
.report-card:nth-child(4) { animation-delay: 0.15s; }
.report-card:nth-child(5) { animation-delay: 0.2s; }
.report-card:nth-child(6) { animation-delay: 0.25s; }

.report-card-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-text);
}

.report-card-icon {
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
}

.report-card-icon--danger {
  background: #fef2f2;
}

.report-card-icon--warning {
  background: #fffbeb;
}

.report-card-icon--info {
  background: #eff6ff;
}

.report-card-icon--success {
  background: #ecfdf5;
}

.report-card-icon--amber {
  background: #fff7ed;
}

.report-card-body {
  /* spacing container */
}

.report-list {
  list-style: none;
  padding: 0;
}

.report-list-item {
  position: relative;
  padding: 10px 0 10px 24px;
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text);
  border-bottom: 1px solid #f1f5f9;
  animation: fadeIn 0.3s ease-out;
  animation-fill-mode: both;
}

.report-list-item:last-child {
  border-bottom: none;
}

.report-list-bullet {
  position: absolute;
  left: 4px;
  top: 16px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.6;
}

.report-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--color-text);
}

.report-card--warning {
  background: linear-gradient(135deg, #fff7ed, #ffedd5);
  border: 1px solid #fed7aa;
}

.report-text--warning {
  font-size: 15px;
  line-height: 1.8;
  color: #9a3412;
  font-weight: 500;
}

/* ============================================================
   过渡动画 (报告进入)
   ============================================================ */

.fadeUp-enter-active {
  animation: fadeInUp 0.4s ease-out;
}

.fadeUp-leave-active {
  animation: fadeIn 0.2s ease-in reverse;
}

/* ============================================================
   数据统计横幅
   ============================================================ */

.stats-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 28px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  border-radius: var(--radius-lg);
  animation: fadeInUp 0.5s ease-out 0.15s both;
}

.stat-item {
  flex: 1;
  text-align: center;
  padding: 4px 8px;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
  line-height: 1.1;
  margin-bottom: 4px;
  background: linear-gradient(135deg, #818cf8, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.2px;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
}

/* ============================================================
   技术卖点区
   ============================================================ */

.tech-section {
  margin-bottom: 20px;
  animation: fadeInUp 0.5s ease-out 0.2s both;
}

.tech-section-header {
  text-align: center;
  margin-bottom: 24px;
}

.tech-section-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: 8px;
  letter-spacing: -0.3px;
}

.tech-section-subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
}

.tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.tech-card {
  background: var(--color-card);
  border-radius: var(--radius);
  padding: 22px 20px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-card-border);
  transition: all var(--transition-slow);
  animation: fadeInUp 0.4s ease-out both;
}

.tech-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-3px);
  border-color: var(--color-primary-light);
}

.tech-card:nth-child(1) { animation-delay: 0.05s; }
.tech-card:nth-child(2) { animation-delay: 0.1s; }
.tech-card:nth-child(3) { animation-delay: 0.15s; }
.tech-card:nth-child(4) { animation-delay: 0.2s; }

.tech-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.tech-card-icon--primary {
  background: #eef2ff;
  color: var(--color-primary);
}

.tech-card-icon--warning {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.tech-card-icon--success {
  background: var(--color-safe-light);
  color: var(--color-safe);
}

.tech-card-icon--info {
  background: #eff6ff;
  color: #3b82f6;
}

.tech-card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.5;
  margin-bottom: 8px;
}

.tech-card-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* ============================================================
   Footer
   ============================================================ */

.footer {
  margin-top: 40px;
  padding-bottom: 20px;
}

.footer-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, var(--color-border), transparent);
  margin-bottom: 20px;
}

.footer-content {
  text-align: center;
}

.footer-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.footer-disclaimer {
  font-size: 12px;
  color: var(--color-text-tertiary);
  line-height: 1.6;
  max-width: 480px;
  margin: 0 auto;
}

/* ============================================================
   响应式
   ============================================================ */

@media (max-width: 640px) {
  .header {
    margin-bottom: 28px;
  }

  .header-badge {
    font-size: 12px;
    padding: 5px 12px;
  }

  .header-title {
    font-size: 24px;
  }

  .header-subtitle {
    font-size: 14px;
  }

  .config-header {
    padding: 16px 20px;
  }

  .config-body {
    padding: 0 20px 20px;
  }

  .upload-zone {
    padding: 24px 16px;
  }

  .risk-banner {
    padding: 16px 20px;
  }

  .risk-tag {
    font-size: 16px;
  }

  .config-btn-row {
    flex-direction: column;
  }

  .report-card-title {
    font-size: 15px;
  }

  .stats-banner {
    padding: 16px 12px;
    border-radius: var(--radius);
    flex-wrap: nowrap;
  }

  .stat-value {
    font-size: 22px;
  }

  .stat-label {
    font-size: 12px;
  }

  .tech-grid {
    grid-template-columns: 1fr;
  }

  .tech-card {
    padding: 18px 16px;
  }

  .tech-section-title {
    font-size: 18px;
  }

  .footer {
    margin-top: 28px;
  }
}
</style>
