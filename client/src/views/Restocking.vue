<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Page chrome (slider) stays visible on load errors so the user can retry or change budget -->
    <div>
      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div class="card budget-card">
        <div class="budget-row">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          step="1000"
          :max="sliderMax"
          :disabled="submitting || loading"
        />
        <div class="budget-scale">
          <span>{{ money(0) }}</span>
          <span>{{ money(sliderMax) }}</span>
        </div>
      </div>

      <div v-if="loadError" class="notice notice-error load-error" role="alert">
        <span>{{ loadError }}</span>
        <button type="button" class="retry-btn" :disabled="loading" @click="retry">{{ t('restocking.retry') }}</button>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(budget) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ moneyPrecise(totalCost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ moneyPrecise(remaining) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">{{ t('restocking.days', { count: leadTimeDays }) }}</div>
        </div>
      </div>

      <div v-if="orderResult" class="notice notice-success">
        {{ t('restocking.orderPlaced', { orderNumber: orderResult.order_number }) }}
        <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
      </div>
      <div v-if="orderError" class="notice notice-error">{{ orderError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ items.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="items.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <!-- Only claim "no items" once a response has actually arrived -->
        <div v-if="items.length === 0" class="empty-state">{{ recommendations ? t('restocking.noItems') : '-' }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.supplier') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td>{{ item.shortfall }}</td>
                <td>
                  <strong>{{ item.quantity }}</strong>
                  <span v-if="item.partial" class="badge warning partial-badge" :title="t('restocking.partialHint')">
                    {{ t('restocking.partial') }}
                  </span>
                </td>
                <td>{{ moneyPrecise(item.unit_cost) }}</td>
                <td><strong>{{ moneyPrecise(item.line_total) }}</strong></td>
                <td>{{ item.supplier_name }}</td>
                <td>{{ t('restocking.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const DEBOUNCE_MS = 250
const STEP = 1000

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const loadError = ref(null)
    const budget = ref(0) // always USD; converted only for display
    const sliderMax = ref(0)
    const recommendations = ref(null)
    const submitting = ref(false)
    const orderResult = ref(null)
    const orderError = ref(null)

    const items = computed(() => recommendations.value?.items ?? [])
    const totalCost = computed(() => recommendations.value?.total_cost ?? 0)
    const remaining = computed(() => recommendations.value?.remaining ?? budget.value)
    const leadTimeDays = computed(() => recommendations.value?.lead_time_days ?? 0)

    const money = (amount) => formatCurrency(amount, currentCurrency.value)
    // Costs need cents: whole-dollar rounding would show $6 for a $6.20 unit cost and hide small remainders
    const moneyPrecise = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

    // Monotonic counter: only the latest request may update state (ignores stale responses)
    let requestId = 0
    let debounceTimer = null
    let initialised = false
    let maxKnown = false // true once a fetch has told us max_budget

    const fetchRecommendations = async () => {
      const id = ++requestId
      try {
        const data = await api.getRestockRecommendations(budget.value)
        if (id !== requestId) return
        recommendations.value = data
        sliderMax.value = Math.max(0, Math.ceil((data.max_budget || 0) / STEP) * STEP)
        loadError.value = null
      } catch (err) {
        if (id !== requestId) return
        loadError.value = t('restocking.loadFailed') + ': ' + (err.response?.data?.detail || err.message)
      }
    }

    const init = async () => {
      loading.value = true
      await fetchRecommendations()
      if (!loadError.value) {
        // max_budget is now known; start at roughly half of what covers every shortfall
        maxKnown = true
        budget.value = Math.round(sliderMax.value / 2 / STEP) * STEP
        await fetchRecommendations()
      }
      initialised = true
      loading.value = false
    }

    // Repeat the initial discovery if it never succeeded, otherwise just refetch for the current budget
    const retry = async () => {
      clearTimeout(debounceTimer)
      if (!maxKnown) return init()
      await fetchRecommendations()
    }

    watch(budget, () => {
      if (!initialised) return
      orderResult.value = null
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(fetchRecommendations, DEBOUNCE_MS)
    })

    const placeOrder = async () => {
      if (submitting.value || items.value.length === 0) return
      submitting.value = true
      orderError.value = null
      orderResult.value = null
      clearTimeout(debounceTimer)
      try {
        const order = await api.createRestockOrder({
          budget: budget.value,
          items: items.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
        })
        orderResult.value = order
        await fetchRecommendations()
      } catch (err) {
        orderError.value = t('restocking.orderFailed') + ': ' + (err.response?.data?.detail || err.message)
        // The cancelled debounce (or a server-side change) may have left the table stale: resync with the current budget
        await fetchRecommendations()
      } finally {
        submitting.value = false
      }
    }

    onMounted(init)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      translateProductName,
      loading,
      loadError,
      recommendations,
      retry,
      budget,
      sliderMax,
      items,
      totalCost,
      remaining,
      leadTimeDays,
      submitting,
      orderResult,
      orderError,
      money,
      moneyPrecise,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--tq-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--tq-blue);
}

.budget-slider {
  width: 100%;
  height: 6px;
  appearance: none;
  background: var(--tq-border);
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  background: var(--tq-blue);
  border: 2px solid white;
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: var(--tq-blue);
  border: 2px solid white;
}

.budget-slider:focus-visible {
  outline: 2px solid var(--tq-light-blue);
  outline-offset: 4px;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: var(--tq-text-muted);
}

.place-order-btn {
  background: var(--tq-lime);
  color: var(--tq-blue);
  border: none;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.35px;
}

.place-order-btn:hover:not(:disabled) {
  background: var(--tq-blue);
}

.place-order-btn:disabled {
  background: var(--tq-border);
  cursor: not-allowed;
}

.partial-badge {
  margin-left: 0.5rem;
}

.notice {
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.notice-success {
  background: var(--ok-bg);
  color: var(--ok);
  border: 1px solid var(--ok);
}

.notice-success a {
  margin-left: 0.5rem;
  font-weight: 700;
  color: var(--ok);
  text-decoration: underline;
}

.notice-error {
  background: var(--bad-bg);
  color: var(--bad);
  border: 1px solid var(--bad);
}

.load-error {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.retry-btn {
  background: var(--bad);
  color: white;
  border: none;
  padding: 0.375rem 1rem;
  font-size: 0.813rem;
  font-weight: 700;
  cursor: pointer;
}

.retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.budget-slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--tq-text-muted);
}
</style>
