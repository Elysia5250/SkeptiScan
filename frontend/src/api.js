/**
 * 后端 API 封装
 * 使用 axios 发送 HTTP 请求
 *
 * 注意：普通查询类接口（status、config）使用短超时，
 * 分析类接口（analyze）使用长超时。
 */

import axios from 'axios'

// 创建 axios 实例，baseURL 由 vite proxy 处理
const api = axios.create({
  baseURL: '',
  timeout: 5000, // 默认 5 秒超时（用于状态检查等轻量请求）
})

/**
 * 分析商品风险
 * 大模型分析可能较慢，使用独立的长超时实例
 * @param {File|null} image - 商品截图文件
 * @param {string|null} url - 商品链接
 * @returns {Promise<object>} { success, mode, report }
 */
export async function analyzeProduct(image = null, url = null) {
  const formData = new FormData()

  if (image) {
    formData.append('image', image)
  }
  if (url) {
    formData.append('url', url)
  }

  const response = await axios.post('/api/analyze', formData, {
    baseURL: '',
    timeout: 120000, // 大模型分析需要更长超时
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

/**
 * 保存 API 运行时配置
 * @param {object} config - { base_url, api_key, model, extra_prompt }
 * @returns {Promise<object>}
 */
export async function saveConfig(config) {
  const formData = new FormData()
  if (config.base_url) formData.append('base_url', config.base_url)
  if (config.api_key) formData.append('api_key', config.api_key)
  if (config.model) formData.append('model', config.model)
  if (config.extra_prompt) formData.append('extra_prompt', config.extra_prompt)

  const response = await api.post('/api/config', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

/**
 * 获取当前配置状态
 * @returns {Promise<object>} { api_configured, base_url, model, extra_prompt_configured, mode }
 */
export async function getConfigStatus() {
  const response = await api.get('/api/config/status')
  return response.data
}

/**
 * 检查后端服务状态
 * @returns {Promise<object>}
 */
export async function getStatus() {
  const response = await api.get('/')
  return response.data
}

export default api