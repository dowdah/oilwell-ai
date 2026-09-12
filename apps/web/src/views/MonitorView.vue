<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getHistory, getLatestInference, getWells, type Inference, type Telemetry } from '../api'

const wells = ref<{ id: string; display_name: string }[]>([])
const selected = ref('')
const samples = ref<Telemetry[]>([])
const inference = ref<Inference | null>(null)
const chartElement = ref<HTMLElement>()
const connectionState = ref('连接中')
const loadError = ref('')
let disposed = false
let loadGeneration = 0
let reconnectTimer: ReturnType<typeof setTimeout> | undefined
let chart: echarts.ECharts | undefined
let socket: WebSocket | undefined
const visibleVariables = ['P_PDG', 'P_TPT', 'T_TPT', 'P_MON_CKP', 'T_JUS_CKP', 'P_JUS_CKGL', 'QGL']
let renderTimer: ReturnType<typeof setTimeout> | undefined
function scheduleRender() { if (!renderTimer) renderTimer = setTimeout(() => { renderTimer = undefined; render() }, 200) }
function resize() { chart?.resize() }

function render() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: visibleVariables.map((_, i) => ({ top: 24 + i * 110, height: 70, left: 100, right: 28 })),
    xAxis: visibleVariables.map((_, i) => ({ gridIndex: i, type: 'category', data: samples.value.map((row) => new Date(row.timestamp).toLocaleTimeString()), axisLabel: { show: i === 6, color: '#8b9bab' } })),
    yAxis: visibleVariables.map((name, i) => ({ gridIndex: i, type: 'value', name, scale: true, axisLabel: { color: '#8b9bab' }, splitLine: { lineStyle: { color: '#213142' } } })),
    series: visibleVariables.map((name, i) => ({ name, type: 'line', xAxisIndex: i, yAxisIndex: i, smooth: false, showSymbol: false, data: samples.value.map((row) => row.measurements[name]) })),
  })
}
async function load() {
  const well = selected.value
  const generation = ++loadGeneration
  if (!well) return
  try {
    const [history, latest] = await Promise.all([getHistory(well), getLatestInference(well).catch(() => null)])
    if (disposed || generation !== loadGeneration || selected.value !== well) return
    samples.value = history.slice(-180)
    inference.value = latest
    loadError.value = ''
    render()
  } catch {
    if (generation === loadGeneration) loadError.value = '历史数据读取失败，请检查连接后重试。'
  }
}
function connect() {
  if (disposed) return
  connectionState.value = '连接中'
  const current = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  socket = current
  current.onopen = () => { connectionState.value = '实时连接正常'; void load() }
  current.onmessage = (event) => {
    const message = JSON.parse(event.data)
    if (message.event === 'telemetry' && message.payload.well_id === selected.value) {
      const previous = samples.value.at(-1)
      if (previous && new Date(message.payload.timestamp).getTime() <= new Date(previous.timestamp).getTime()) samples.value = []
      samples.value = [...samples.value.slice(-179), message.payload]; scheduleRender()
    }
    if (message.event === 'inference' && message.payload.well_id === selected.value && message.payload.model_mode === 'active') inference.value = message.payload
  }
  current.onclose = () => {
    if (disposed || socket !== current) return
    connectionState.value = '连接中断，正在重连'
    reconnectTimer = setTimeout(connect, 2000)
  }
  current.onerror = () => current.close()
}
watch(selected, () => { samples.value = []; inference.value = null; render(); void load() })
onMounted(async () => {
  await nextTick()
  if (chartElement.value) chart = echarts.init(chartElement.value)
  try { wells.value = await getWells(); selected.value = wells.value[0]?.id ?? '' }
  catch { loadError.value = '油井列表读取失败，请检查服务连接。' }
  connect()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  disposed = true; loadGeneration += 1
  socket?.close(); chart?.dispose(); window.removeEventListener('resize', resize)
  if (renderTimer) clearTimeout(renderTimer)
  if (reconnectTimer) clearTimeout(reconnectTimer)
})
</script>

<template>
  <div class="view"><div class="view-title"><div><h2>实时监测</h2><p>固定 7 变量契约；显示 XGBoost 活动模型结论，TCN 对照位于模型中心</p></div><select v-model="selected" aria-label="选择油井"><option disabled value="">选择油井</option><option v-for="well in wells" :key="well.id" :value="well.id">{{ well.display_name }}</option></select></div><section class="panel chart-panel"><p role="status">{{ connectionState }}</p><p v-if="loadError" role="alert">{{ loadError }}</p><div class="prediction"><div><span>当前活动推理</span><strong>{{ inference?.predicted_class ?? '等待模型制品' }}</strong></div><div><span>窗口状态</span><strong>{{ inference?.status ?? '无推理记录' }}</strong></div><div><span>置信度 / 异常分数</span><strong class="normal">{{ inference?.confidence != null ? `${(inference.confidence * 100).toFixed(1)}% / ${(inference.anomaly_score! * 100).toFixed(1)}%` : '—' }}</strong></div><small class="prediction-note">模型输出仅用于辅助分析与教学演示，不构成现场操作指令。</small></div><div ref="chartElement" class="chart" style="height:800px" aria-label="传感器实时趋势图"></div></section></div>
</template>
