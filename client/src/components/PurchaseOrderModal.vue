<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <h4 class="item-name">{{ translateProductName(backlogItem.item_name) }}</h4>
              <div class="item-sku">SKU: {{ backlogItem.item_sku }}</div>
            </div>

            <!-- View mode -->
            <template v-if="mode === 'view'">
              <div v-if="loading" class="loading-state">{{ t('common.loading') }}</div>
              <div v-else-if="error" class="error-message">{{ error }}</div>
              <template v-else-if="purchaseOrder">
                <div class="info-grid view-grid">
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.poId') }}</div>
                    <div class="info-value sku">{{ purchaseOrder.id }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                    <div class="info-value"><span class="badge">{{ purchaseOrder.status }}</span></div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                    <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                    <div class="info-value">{{ purchaseOrder.quantity }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                    <div class="info-value">{{ formatCurrencyWithDecimals(purchaseOrder.unit_cost, currentCurrency, 2) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.total') }}</div>
                    <div class="info-value">{{ formatCurrencyWithDecimals(purchaseOrder.quantity * purchaseOrder.unit_cost, currentCurrency, 2) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                    <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                    <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                  </div>
                </div>
                <div v-if="purchaseOrder.notes" class="info-item po-notes">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ purchaseOrder.notes }}</div>
                </div>
              </template>
            </template>

            <!-- Create mode -->
            <form v-else id="po-form" class="form-grid" novalidate @submit.prevent="submit">
              <div class="form-field full">
                <label class="info-label" for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                <input id="po-supplier" v-model.trim="form.supplier_name" class="form-input"
                       :class="{ invalid: errors.supplier_name }" type="text" />
                <span v-if="errors.supplier_name" class="field-error">{{ errors.supplier_name }}</span>
              </div>
              <div class="form-field">
                <label class="info-label" for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                <input id="po-quantity" v-model.number="form.quantity" class="form-input"
                       :class="{ invalid: errors.quantity }" type="number" min="1" step="1" />
                <span v-if="errors.quantity" class="field-error">{{ errors.quantity }}</span>
              </div>
              <div class="form-field">
                <label class="info-label" for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                <input id="po-unit-cost" v-model.number="form.unit_cost" class="form-input"
                       :class="{ invalid: errors.unit_cost }" type="number" min="0" step="0.01" />
                <span v-if="errors.unit_cost" class="field-error">{{ errors.unit_cost }}</span>
              </div>
              <div class="form-field full">
                <label class="info-label" for="po-date">{{ t('purchaseOrder.expectedDelivery') }}</label>
                <input id="po-date" v-model="form.expected_delivery_date" class="form-input"
                       :class="{ invalid: errors.expected_delivery_date }" type="date" />
                <span v-if="errors.expected_delivery_date" class="field-error">{{ errors.expected_delivery_date }}</span>
              </div>
              <div class="form-field full">
                <label class="info-label" for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea id="po-notes" v-model="form.notes" class="form-input" rows="3"></textarea>
              </div>
              <div v-if="error" class="error-message form-field full">{{ error }}</div>
            </form>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" type="button" @click="close">{{ t('common.close') }}</button>
            <button v-if="mode === 'create'" class="btn-primary" type="submit" form="po-form" :disabled="submitting">
              {{ submitting ? t('purchaseOrder.creating') : t('purchaseOrder.create') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentCurrency, translateProductName } = useI18n()

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
})

const emit = defineEmits(['close', 'po-created'])

const loading = ref(false)
const submitting = ref(false)
const error = ref(null)
const purchaseOrder = ref(null)
const errors = reactive({})
const form = reactive({
  supplier_name: '',
  quantity: 1,
  unit_cost: 0,
  expected_delivery_date: '',
  notes: ''
})

const close = () => emit('close')

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const resetForm = () => {
  const item = props.backlogItem
  // Default the order quantity to the shortage so the PO covers the gap
  const shortage = item ? item.quantity_needed - item.quantity_available : 1
  form.supplier_name = ''
  form.quantity = shortage > 0 ? shortage : 1
  form.unit_cost = 0
  form.expected_delivery_date = ''
  form.notes = ''
  Object.keys(errors).forEach((k) => delete errors[k])
}

const loadPO = async () => {
  loading.value = true
  try {
    purchaseOrder.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    error.value = t('purchaseOrder.loadError')
    console.error('Failed to load purchase order:', err)
  } finally {
    loading.value = false
  }
}

// Mirrors the server rules (quantity > 0) so users get feedback before a round trip
const validate = () => {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.supplier_name) errors.supplier_name = t('purchaseOrder.supplierRequired')
  if (!Number.isInteger(form.quantity) || form.quantity <= 0) errors.quantity = t('purchaseOrder.quantityInvalid')
  if (typeof form.unit_cost !== 'number' || isNaN(form.unit_cost) || form.unit_cost < 0) {
    errors.unit_cost = t('purchaseOrder.unitCostInvalid')
  }
  if (!form.expected_delivery_date) errors.expected_delivery_date = t('purchaseOrder.dateRequired')
  return Object.keys(errors).length === 0
}

const submit = async () => {
  if (submitting.value || !validate()) return
  submitting.value = true
  error.value = null
  try {
    const created = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.supplier_name,
      quantity: form.quantity,
      unit_cost: form.unit_cost,
      expected_delivery_date: form.expected_delivery_date,
      // Send null rather than '' so the backend stores "no notes"
      notes: form.notes.trim() || null
    })
    emit('po-created', created)
  } catch (err) {
    // 409 = a PO already exists for this backlog item
    error.value = err.response?.status === 409
      ? t('purchaseOrder.alreadyExists')
      : t('purchaseOrder.createError')
    console.error('Failed to create purchase order:', err)
  } finally {
    submitting.value = false
  }
}

// Reinitialise each time the modal opens (the component stays mounted between opens)
watch(
  () => [props.isOpen, props.backlogItem, props.mode],
  () => {
    if (!props.isOpen || !props.backlogItem) return
    error.value = null
    purchaseOrder.value = null
    if (props.mode === 'view') loadPO()
    else resetForm()
  },
  { immediate: true }
)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.shortage-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1.5rem;
}

.shortage-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.shortage-title-section {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.item-sku {
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.priority-badge {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  flex-shrink: 0;
}

.priority-badge.high {
  background: #fecaca;
  color: #991b1b;
}

.priority-badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.priority-badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.shortage-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  padding: 1.25rem;
  border-radius: 10px;
  border: 2px solid;
}

.summary-card.danger {
  border-color: #fecaca;
  background: #fef2f2;
}

.summary-card.warning {
  border-color: #fed7aa;
  background: #fffbeb;
}

.summary-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
}

.summary-card.danger .summary-value {
  color: #dc2626;
}

.summary-card.warning .summary-value {
  color: #f59e0b;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.info-value.order-id,
.info-value.sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.loading-state,
.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.875rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-top: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field.full {
  grid-column: 1 / -1;
}

.form-input {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.938rem;
  color: #0f172a;
  font-family: inherit;
}

.form-input:focus {
  outline: none;
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.15);
}

.form-input.invalid {
  border-color: #ef4444;
}

.field-error {
  font-size: 0.813rem;
  color: #dc2626;
}

.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #0f172a;
  border: 1px solid #0f172a;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.po-notes {
  margin-top: 1.5rem;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  background: #dbeafe;
  color: #1e40af;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}

.item-summary {
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 0.5rem;
}

.item-summary .item-name {
  font-size: 1.25rem;
  margin-bottom: 0.25rem;
}
</style>
