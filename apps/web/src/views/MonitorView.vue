<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getHistory, getLatestInference, getWells, type Inference, type Telemetry } from '../api'

const wells = ref<{ id: string; display_name: string }[]>([])
const selected = ref('')
const samples = ref<Telemetry[]>([])
const inference = ref<Inference | null>(null)
const chartElement = ref<HTMLElement>()
let chart: echarts.ECharts | undefined
let socket: WebSocket | undefined
const visibleVariables = ['P_PDG', 'P_TPT', 'T_TPT', 'QGL']

function render() {
  if (!chart) return
  chart.setOption({ tooltip: { trigger: 'axis' }, legend: { top: 0, textStyle: { color: '#9eafbd' } }, grid: { top: 50, left: 56, right: 24, bottom: 42 }, xAxis: { type: 'category', data: samples.value.map((s) => new Date(s.timestamp).toLocaleTimeString()), axisLabel: { color: '#8b9bab' } }, yAxis: { type: 'value', scale: true, axisLabel: { color: '#8b9bab' }, splitLine: { lineStyle: { color: '#213142' } } }, series: visibleVariables.map((key) => ({ name: key, type: 'line', smooth: true, showSymbol: false, data: samples.value.map((s) => s.measurements[key]), })) })
}
async function load() {
  if (!selected.value) return
  samples.value = await getHistory(selected.value)
  try { inference.value = await getLatestInference(selected.value) } catch { inference.value = null }
  render()
}
watch(selected, load)
onMounted(async () => {
  wells.value = await getWells(); selected.value = wells.value[0]?.id ?? ''
  await nextTick(); if (chartElement.value) chart = echarts.init(chartElement.value); await load()
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data)
    if (message.event === 'telemetry' && message.payload.well_id === selected.value) {
      samples.value = [...samples.value.slice(-359), message.payload]; render()
    }
    if (message.event === 'inference' && message.payload.well_id === selected.value && message.payload.model_mode === 'active') inference.value = message.payload
  }
  window.addEventListener('resize', render)
})
onBeforeUnmount(() => { socket?.close(); chart?.dispose(); window.removeEventListener('resize', render) })
</script>

<template>
  <div class="view"><div class="view-title"><div><h2>实时监测</h2><p>固定 7 变量契约；显示 XGBoost 活动模型结论，TCN 对照位于模型中心</p></div><select v-model="selected" aria-label="选择油井"><option disabled value="">选择油井</option><option v-for="well in wells" :key="well.id" :value="well.id">{{ well.display_name }}</option></select></div><section class="panel chart-panel"><div class="prediction"><div><span>当前活动推理</span><strong>{{ inference?.predicted_class ?? '等待模型制品' }}</strong></div><div><span>窗口状态</span><strong>{{ inference?.status ?? '无推理记录' }}</strong></div><div><span>置信度 / 异常分数</span><strong class="normal">{{ inference?.confidence != null ? `${(inference.confidence * 100).toFixed(1)}% / ${(inference.anomaly_score! * 100).toFixed(1)}%` : '—' }}</strong></div><small class="prediction-note">模型输出仅用于辅助分析与教学演示，不构成现场操作指令。</small></div><div ref="chartElement" class="chart" aria-label="传感器实时趋势图"></div></section></div>
</template>
