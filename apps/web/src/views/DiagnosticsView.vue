<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { createDiagnostic, getDiagnostics, getLatestComparison, getWells, type Diagnostic, type Inference } from '../api'

const wells = ref<{ id: string; display_name: string }[]>([])
const selected = ref('')
const comparison = ref<Inference[]>([])
const records = ref<Diagnostic[]>([])
const busy = ref(false)
const error = ref('')
const active = computed(() => comparison.value.find((item) => item.model_mode === 'active'))

async function load() {
  if (!selected.value) return
  try {
    const [latest, history] = await Promise.all([getLatestComparison(selected.value), getDiagnostics(selected.value)])
    comparison.value = latest; records.value = history; error.value = ''
  } catch { comparison.value = []; records.value = []; error.value = '暂无可用完整窗口或诊断记录。' }
}
async function generate() {
  if (!selected.value || !active.value) return
  busy.value = true; error.value = ''
  try { records.value.unshift(await createDiagnostic(selected.value, active.value.id)) }
  catch { error.value = '生成诊断失败，请确认 API 与已选 active 推理结果可用。' }
  finally { busy.value = false }
}
async function initialLoad() {
  try { wells.value = await getWells(); selected.value ||= wells.value[0]?.id ?? ''; await load() }
  catch { error.value = '无法读取油井列表。请确认 API 已启动。' }
}
watch(selected, load)
onMounted(initialLoad)
</script>

<template>
  <div class="view">
    <div class="view-title"><div><h2>辅助诊断</h2><p>只使用已验证的模型结果、离线解释摘要和已审阅公开资料。</p></div><button class="secondary" @click="load">刷新</button></div>
    <p v-if="error" class="hint">{{ error }}</p>
    <section class="panel diagnostic-controls">
      <label>油井<select v-model="selected" aria-label="选择油井"><option disabled value="">选择油井</option><option v-for="well in wells" :key="well.id" :value="well.id">{{ well.display_name }}</option></select></label>
      <div v-if="active" class="diagnostic-result"><span>只读输入</span><strong>{{ active.model_type }} / {{ active.model_version ?? '—' }}</strong><small>窗口 {{ active.window_start ?? '—' }} 至 {{ active.window_end ?? '—' }}；结论 {{ active.predicted_class ?? active.status }}，置信度 {{ active.confidence != null ? `${(active.confidence * 100).toFixed(1)}%` : '—' }}</small></div>
      <button :disabled="!active || busy" @click="generate">{{ busy ? '生成中…' : '生成受控诊断' }}</button>
    </section>
    <section v-for="record in records" :key="record.id" class="panel diagnostic-record">
      <div class="panel-head"><h3>{{ record.status === 'completed' ? '诊断记录' : '拒答记录' }}</h3><span>{{ record.created_at }}</span></div>
      <p>{{ record.content }}</p>
      <dl class="model-details"><dt>请求 ID</dt><dd>{{ record.request_id }}</dd><dt>模型 / 知识库</dt><dd>{{ record.model_version ?? '—' }} / {{ record.knowledge_base_version }}</dd><dt>证据状态</dt><dd>{{ record.evidence_status === 'complete' ? '完整' : record.evidence_status === 'degraded' ? '安全降级' : '拒答' }}</dd><dt>解释制品</dt><dd>{{ record.explanation_version ?? '同窗口摘要不可用' }}</dd><dt v-if="record.degradation_reasons.length">降级/拒答原因</dt><dd v-if="record.degradation_reasons.length">{{ record.degradation_reasons.join('；') }}</dd></dl>
      <div v-if="record.citations.length" class="citations"><h4>可追溯资料</h4><a v-for="citation in record.citations" :key="citation.id" :href="citation.url" target="_blank" rel="noreferrer">[{{ citation.id }}] {{ citation.title }} <small>{{ citation.version }} · {{ citation.license }}</small></a></div>
    </section>
    <section v-if="!records.length" class="panel empty">选择有完整窗口的油井后可生成第一条受控诊断。</section>
  </div>
</template>
