<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getLatestComparison, getModels, getWells, type Inference, type ModelStatus } from '../api'

const models = ref<ModelStatus[]>([])
const wells = ref<{ id: string; display_name: string }[]>([])
const selected = ref('')
const comparison = ref<Inference[]>([])
const error = ref('')
const active = computed(() => models.value.find((model) => model.mode === 'active'))
const shadow = computed(() => models.value.find((model) => model.mode === 'shadow'))

async function loadComparison() {
  if (!selected.value) return
  try { comparison.value = await getLatestComparison(selected.value) } catch { comparison.value = [] }
}
async function load() {
  try {
    const [modelData, wellData] = await Promise.all([getModels(), getWells()])
    models.value = modelData; wells.value = wellData; selected.value ||= wells.value[0]?.id ?? ''
    await loadComparison()
  } catch { error.value = '无法读取模型状态。请确认 API 已启动。' }
}
watch(selected, loadComparison)
onMounted(load)
</script>

<template>
  <div class="view">
    <div class="view-title"><div><h2>模型中心</h2><p>Active 模型产生报警；TCN 仅进行影子推理和对照。</p></div><button class="secondary" @click="load">刷新</button></div>
    <p v-if="error" class="hint">{{ error }}</p>
    <section class="two-column">
      <article v-for="model in [active, shadow]" :key="model?.mode" class="panel">
        <div class="panel-head"><h3>{{ model?.mode === 'active' ? '活动报警模型' : 'Shadow 对照模型' }}</h3><span>{{ model?.status ?? 'unavailable' }}</span></div>
        <dl class="model-details"><dt>模型</dt><dd>{{ model?.model_type ?? '未加载' }}</dd><dt>版本</dt><dd>{{ model?.version ?? '—' }}</dd><dt>训练数据</dt><dd>{{ model?.training_data_version ?? '—' }}</dd><dt>测试 Macro F1</dt><dd>{{ model?.metrics?.macro_f1 != null ? Number(model.metrics.macro_f1).toFixed(4) : '—' }}</dd><dt>CPU 延迟</dt><dd>{{ model?.metrics?.cpu_inference_latency_ms_per_window != null ? `${Number(model.metrics.cpu_inference_latency_ms_per_window).toFixed(2)} ms/窗口` : '—' }}</dd><dt v-if="model?.error">加载说明</dt><dd v-if="model?.error">{{ model.error }}</dd></dl>
      </article>
    </section>
    <section class="panel table-panel"><div class="panel-head"><h3>同一窗口的最新对照</h3><select v-model="selected" aria-label="选择油井"><option disabled value="">选择油井</option><option v-for="well in wells" :key="well.id" :value="well.id">{{ well.display_name }}</option></select></div><table><thead><tr><th>模式</th><th>模型</th><th>结论</th><th>置信度</th><th>异常分数</th><th>推理延迟</th></tr></thead><tbody><tr v-for="item in comparison" :key="item.id"><td>{{ item.model_mode }}</td><td>{{ item.model_type }} / {{ item.model_version ?? '—' }}</td><td>{{ item.predicted_class ?? item.status }}</td><td>{{ item.confidence != null ? `${(item.confidence * 100).toFixed(1)}%` : '—' }}</td><td>{{ item.anomaly_score != null ? `${(item.anomaly_score * 100).toFixed(1)}%` : '—' }}</td><td>{{ item.inference_latency_ms != null ? `${item.inference_latency_ms.toFixed(2)} ms` : '—' }}</td></tr><tr v-if="!comparison.length"><td colspan="6" class="empty">等待一个完整的 180 秒窗口；无 TCN 制品时仅显示活动模型。</td></tr></tbody></table></section>
  </div>
</template>
