<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getHistory, getWells, type Telemetry } from '../api'

const wells = ref<{ id: string; display_name: string }[]>([])
const selected = ref('')
const samples = ref<Telemetry[]>([])
const chartElement = ref<HTMLElement>()
let chart: echarts.ECharts | undefined
let socket: WebSocket | undefined
const visibleVariables = ['P_PDG', 'P_TPT', 'T_TPT', 'QGL']

function render() {
  if (!chart) return
  chart.setOption({ tooltip: { trigger: 'axis' }, legend: { top: 0, textStyle: { color: '#9eafbd' } }, grid: { top: 50, left: 56, right: 24, bottom: 42 }, xAxis: { type: 'category', data: samples.value.map((s) => new Date(s.timestamp).toLocaleTimeString()), axisLabel: { color: '#8b9bab' } }, yAxis: { type: 'value', scale: true, axisLabel: { color: '#8b9bab' }, splitLine: { lineStyle: { color: '#213142' } } }, series: visibleVariables.map((key) => ({ name: key, type: 'line', smooth: true, showSymbol: false, data: samples.value.map((s) => s.measurements[key]), })) })
}
async function load() { if (selected.value) { samples.value = await getHistory(selected.value); render() } }
watch(selected, load)
onMounted(async () => {
  wells.value = await getWells(); selected.value = wells.value[0]?.id ?? ''
  await nextTick(); if (chartElement.value) chart = echarts.init(chartElement.value); await load()
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  socket.onmessage = (event) => { const message = JSON.parse(event.data); if (message.event === 'telemetry' && message.payload.well_id === selected.value) { samples.value = [...samples.value.slice(-359), message.payload]; render() } }
  window.addEventListener('resize', render)
})
onBeforeUnmount(() => { socket?.close(); chart?.dispose(); window.removeEventListener('resize', render) })
</script>

<template>
  <div class="view"><div class="view-title"><div><h2>实时监测</h2><p>固定 7 变量契约；当前显示四条关键趋势</p></div><select v-model="selected" aria-label="选择油井"><option disabled value="">选择油井</option><option v-for="well in wells" :key="well.id" :value="well.id">{{ well.display_name }}</option></select></div><section class="panel chart-panel"><div class="prediction"><div><span>当前推理</span><strong>等待模型制品</strong></div><div><span>实时窗口</span><strong>{{ samples.length }} / 180</strong></div><div><span>状态</span><strong class="normal">数据流正常</strong></div></div><div ref="chartElement" class="chart" aria-label="传感器实时趋势图"></div></section></div>
</template>
