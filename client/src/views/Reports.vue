<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('reports.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div v-if="monthlyData.length === 0" class="card empty">{{ t('common.noData') }}</div>
      <template v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterlyPerformance') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarter') }}</th>
                <th>{{ t('reports.totalOrders') }}</th>
                <th>{{ t('reports.totalRevenue') }}</th>
                <th>{{ t('reports.avgOrderValue') }}</th>
                <th>{{ t('reports.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ formatQuarter(q.quarter) }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ money(q.total_revenue) }}</td>
                <td>{{ money(q.avg_order_value) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthlyRevenueTrend') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="money(month.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.momAnalysis') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.month') }}</th>
                <th>{{ t('reports.orders') }}</th>
                <th>{{ t('reports.revenue') }}</th>
                <th>{{ t('reports.change') }}</th>
                <th>{{ t('reports.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(month, index) in monthlyData" :key="month.month">
                <td><strong>{{ formatMonth(month.month) }}</strong></td>
                <td>{{ month.order_count }}</td>
                <td>{{ money(month.revenue) }}</td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getChangeValue(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getGrowthRate(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.totalRevenueYtd') }}</div>
          <div class="stat-value">{{ money(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ money(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.totalOrdersYtd') }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter ? formatQuarter(bestQuarter) : '-' }}</div>
        </div>
      </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Reports',
  setup() {
    const { t, currentLocale, currentCurrency } = useI18n()
    const { selectedPeriod, selectedLocation, selectedCategory, selectedStatus, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])

    // The /api/reports/* endpoints ignore filters, so build the reports from the
    // filtered /api/orders response instead. This keeps the global filter bar working.
    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        orders.value = await api.getOrders(getCurrentFilters())
      } catch (err) {
        error.value = t('reports.loadError') + ': ' + err.message
        console.error('Failed to load reports:', err)
      } finally {
        loading.value = false
      }
    }

    // Parse once; orders with a missing/invalid date are skipped (cannot be bucketed)
    const datedOrders = computed(() => {
      return orders.value
        .map(o => ({ order: o, date: new Date(o.order_date) }))
        .filter(({ date }) => !isNaN(date.getTime()))
    })

    // Group by YYYY-MM, sorted chronologically
    const monthlyData = computed(() => {
      const months = {}
      for (const { order, date } of datedOrders.value) {
        const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        if (!months[key]) months[key] = { month: key, order_count: 0, revenue: 0 }
        months[key].order_count += 1
        months[key].revenue += order.total_value || 0
      }
      return Object.values(months).sort((a, b) => a.month.localeCompare(b.month))
    })

    // Group by calendar quarter; fulfillment rate = share of delivered orders
    const quarterlyData = computed(() => {
      const quarters = {}
      for (const { order, date } of datedOrders.value) {
        const key = `${date.getFullYear()}-Q${Math.floor(date.getMonth() / 3) + 1}`
        if (!quarters[key]) quarters[key] = { quarter: key, total_orders: 0, total_revenue: 0, delivered: 0 }
        quarters[key].total_orders += 1
        quarters[key].total_revenue += order.total_value || 0
        if (order.status === 'Delivered') quarters[key].delivered += 1
      }
      return Object.values(quarters)
        .sort((a, b) => a.quarter.localeCompare(b.quarter))
        .map(q => ({
          ...q,
          avg_order_value: q.total_orders ? q.total_revenue / q.total_orders : 0,
          fulfillment_rate: q.total_orders ? Math.round((q.delivered / q.total_orders) * 1000) / 10 : 0
        }))
    })

    const totalRevenue = computed(() => monthlyData.value.reduce((sum, m) => sum + m.revenue, 0))
    const totalOrders = computed(() => monthlyData.value.reduce((sum, m) => sum + m.order_count, 0))
    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length ? totalRevenue.value / monthlyData.value.length : 0
    )

    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (!best || q.total_revenue > best.total_revenue) best = q
      }
      return best ? best.quarter : ''
    })

    // Computed once instead of scanning all months for every bar on every render
    const maxRevenue = computed(() => Math.max(0, ...monthlyData.value.map(m => m.revenue)))

    const money = (amount) => formatCurrency(amount, currentCurrency.value)

    // "2025-Q1" -> localized label
    const formatQuarter = (key) => {
      const [year, q] = key.split('-Q')
      return t('reports.quarterLabel', { year, quarter: q })
    }

    const formatMonth = (monthStr) => {
      const [year, month] = monthStr.split('-').map(Number)
      const date = new Date(year, month - 1, 1)
      if (isNaN(date.getTime())) return monthStr
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short'
      })
    }

    // Max bar height is 200px (matches .bar-container)
    const getBarHeight = (revenue) => (maxRevenue.value === 0 ? 0 : (revenue / maxRevenue.value) * 200)

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'badge success'
      if (rate >= 75) return 'badge warning'
      return 'badge danger'
    }

    const getChangeClass = (current, previous) => {
      const change = current - previous
      if (change > 0) return 'positive-change'
      if (change < 0) return 'negative-change'
      return ''
    }

    const getChangeValue = (current, previous) => {
      const change = current - previous
      if (change > 0) return '+' + money(change)
      if (change < 0) return '-' + money(Math.abs(change))
      return money(0)
    }

    const getGrowthRate = (current, previous) => {
      if (previous === 0) return t('reports.notAvailable')
      const rate = ((current - previous) / previous) * 100
      return (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
    }

    // Reload on any global filter change (all four affect /api/orders)
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], loadData)

    onMounted(loadData)

    return {
      t, loading, error, quarterlyData, monthlyData, totalRevenue, avgMonthlyRevenue, totalOrders, bestQuarter,
      money, formatQuarter, formatMonth, getBarHeight, getFulfillmentClass,
      getChangeClass, getChangeValue, getGrowthRate
    }
  }
}
</script>

<style scoped>
.reports {
  padding: 0;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 1.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: #f8fafc;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.reports-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.reports-table tr:hover {
  background: #f8fafc;
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #3b82f6;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.badge.success {
  background: #dcfce7;
  color: #166534;
}

.badge.warning {
  background: #fef3c7;
  color: #92400e;
}

.badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}

.empty {
  text-align: center;
  color: #64748b;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}
</style>
