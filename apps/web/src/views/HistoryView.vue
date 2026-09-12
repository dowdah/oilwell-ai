<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getWells, getHistory, getInferenceHistory, type Inference, type Telemetry } from '../api'
const wells = ref<{id: string; display_name: string}[]>([])
const well = ref(''), start = ref(''), end = ref(''), eventClass = ref(''), error = ref('')
const rows = ref<Telemetry[]>([]), predictions = ref<Inference[]>([]), loading = ref(false)
const variables = ['P_PDG', 'P_TPT', 'T_TPT', 'P_MON_CKP', 'T_JUS_CKP', 'P_JUS_CKGL', 'QGL']
async function load() {
  if (!well.value) return
  loading.value = true; error.value = ''
  try {
    const params = { limit: 500, start: start.value ? new Date(start.value).toISOString() : undefined, end: end.value ? new Date(end.value).toISOString() : undefined }
    ;[rows.value, predictions.value] = await Promise.all([getHistory(well.value, params), getInferenceHistory(well.value, { ...params, mode: 'active', event_class: eventClass.value || undefined })])
  } catch { error.value = '查询失败，请检查起止时间和服务连接。' }
  finally { loading.value = false }
}
onMounted(async () => { try { wells.value = await getWells(); well.value = wells.value[0]?.id ?? ''; await load() } catch { error.value = '无法获取油井列表。' } })
</script>
<template>
  <div class="view">
    <div class="view-title"><div><h2>历史事件</h2><p>按原始采样时间查询；每次最多显示 500 条，更多记录请缩小时间范围。</p></div></div>
    <form class="panel" style="display:flex;flex-wrap:wrap;gap:16px;padding:20px" @submit.prevent="load">
      <label>油井 <select v-model="well"><option v-for="item in wells" :key="item.id" :value="item.id">{{ item.display_name }}</option></select></label>
      <label>开始时间 <input v-model="start" type="datetime-local" /></label><label>结束时间 <input v-model="end" type="datetime-local" /></label>
      <label>模型类别 <select v-model="eventClass"><option value="">全部类别</option><option v-for="item in ['Normal','Severe Slugging','Flow Instability','Hydrate in Service Line']" :key="item">{{ item }}</option></select></label>
      <button :disabled="loading || !well">{{ loading ? '查询中…' : '查询' }}</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <section class="panel table-panel"><h3>活动模型事件（{{ predictions.length }}）</h3><table><thead><tr><th>窗口结束</th><th>模型类别</th><th>置信度</th><th>版本</th></tr></thead><tbody><tr v-for="item in predictions" :key="item.id"><td>{{ item.window_end ? new Date(item.window_end).toLocaleString() : '预热中' }}</td><td>{{ item.predicted_class ?? item.status }}</td><td>{{ item.confidence == null ? '—' : `${(item.confidence*100).toFixed(1)}%` }}</td><td>{{ item.model_version }}</td></tr></tbody></table><p v-if="!predictions.length" class="empty">当前条件下无推理记录。</p></section>
    <section class="panel table-panel" style="overflow-x:auto"><h3>同时间范围传感器记录（{{ rows.length }}）</h3><table><thead><tr><th>采样时间</th><th v-for="name in variables" :key="name">{{ name }}</th></tr></thead><tbody><tr v-for="item in rows" :key="item.sequence"><td>{{ new Date(item.timestamp).toLocaleString() }}</td><td v-for="name in variables" :key="name">{{ item.measurements[name]?.toPrecision(5) }}</td></tr></tbody></table><p v-if="!rows.length" class="empty">当前时间范围无遥测记录。</p></section>
  </div>
</template>
