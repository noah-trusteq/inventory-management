<template>
  <div class="app">
    <header class="top-nav">
      <div class="nav-container">
        <div class="logo">
          <img :src="logoUrl" alt="TRUSTEQ" />
        </div>
        <nav class="nav-tabs">
          <router-link to="/" :class="{ active: $route.path === '/' }">
            {{ t('nav.overview') }}
          </router-link>
          <router-link to="/inventory" :class="{ active: $route.path === '/inventory' }">
            {{ t('nav.inventory') }}
          </router-link>
          <router-link to="/orders" :class="{ active: $route.path === '/orders' }">
            {{ t('nav.orders') }}
          </router-link>
          <router-link to="/spending" :class="{ active: $route.path === '/spending' }">
            {{ t('nav.finance') }}
          </router-link>
          <router-link to="/demand" :class="{ active: $route.path === '/demand' }">
            {{ t('nav.demandForecast') }}
          </router-link>
          <router-link to="/restocking" :class="{ active: $route.path === '/restocking' }">
            {{ t('nav.restocking') }}
          </router-link>
          <router-link to="/reports" :class="{ active: $route.path === '/reports' }">
            {{ t('nav.reports') }}
          </router-link>
        </nav>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
        <!-- Decorative square motif from the TRUSTEQ brand grid -->
        <div class="nav-motif" aria-hidden="true">
          <span></span><span></span><span></span><span></span>
        </div>
      </div>
    </header>
    <FilterBar />
    <main class="main-content">
      <router-view />
    </main>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import logoUrl from './assets/trusteq-logo-light.svg'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      logoUrl,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* TRUSTEQ palette */
  --tq-blue: #003366;
  --tq-navy-2: #004181;
  --tq-light-blue: #0069D1;
  --tq-tint: #EBF1FB;
  --tq-grey: #EEEFF0;
  --tq-border: #C3C3C9; /* borders/dividers only, never text */
  --tq-bg: #FCFDFE; /* page background */
  --white: #ffffff;
  --tq-gold: #AE9966; /* logo and tiny motifs only */
  --tq-lime: #DAFF7D; /* accent: primary buttons (navy text) and marks on navy; never text on light */
  --tq-sand: #E7E0D0; /* secondary buttons (navy text) */
  /* Muted text: darkened navy-grey so it keeps AA on white, bg and tint fills */
  --tq-text-muted: #4A5D73;
  --tq-overlay: rgba(0, 51, 102, 0.6);

  /* Semantic status set: dark text/solid on tinted background, label always shown */
  --ok: #1B6B47;
  --ok-bg: #E3F1E9;
  --warn: #8A5300;
  --warn-bg: #FAEEDA;
  --bad: #B3261E;
  --bad-bg: #FBE7E5;
  --info: var(--tq-light-blue);
  --info-bg: var(--tq-tint);

  /* Categorical chart palette (blues + grey), shared by all pages */
  --chart-1: #003366;
  --chart-2: #0069D1;
  --chart-3: #6B7C93;
  --chart-4: #8FB5E8;
  --chart-5: #C3C3C9;

  --font-body: 'Karla', -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', 'Segoe UI', sans-serif;
  /* Karla has no Japanese glyphs; serif fallbacks keep headings in the same register */
  --font-heading: 'Lora', Georgia, 'Hiragino Mincho ProN', 'Yu Mincho', serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-body);
  font-weight: 400;
  background: var(--tq-bg);
  color: var(--tq-blue);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button,
input,
select,
textarea {
  font-family: inherit;
}

/* Lora is only loaded at 500, so force it to avoid faux-bold on component headings */
h1, h2, h3, h4 {
  font-family: var(--font-heading);
  color: var(--tq-blue);
}

h1:not(.section-title), h2:not(.section-title), h3:not(.section-title), h4:not(.section-title) {
  font-weight: 500 !important;
}

th, label, strong, b {
  font-weight: 700;
}

a {
  color: var(--tq-light-blue);
}

:focus-visible {
  outline: 2px solid var(--tq-light-blue);
  outline-offset: 2px;
}

ul:not([class]) {
  list-style: none;
}

ul:not([class]) > li::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 0.5rem;
  background: var(--tq-blue);
  vertical-align: middle;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Full-width navy band, white text */
.top-nav {
  background: var(--tq-blue);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  min-height: 72px;
  flex-wrap: wrap;
  gap: 0 0.5rem;
}

.nav-container > .nav-tabs {
  margin-left: auto;
  margin-right: 0.5rem;
}

.logo {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-right: 1rem;
}

.logo img {
  display: block;
  height: 30px;
  width: auto;
}

.nav-tabs {
  display: flex;
  gap: 0.25rem;
}

/* Active/hover state is a lime underline, not a filled box */
.nav-tabs a {
  padding: 1.25rem 0.75rem 1.0625rem;
  color: var(--white);
  text-decoration: none;
  font-weight: 400;
  font-size: 0.938rem;
  white-space: nowrap;
  border-bottom: 3px solid transparent;
}

.nav-tabs a:hover {
  border-bottom-color: var(--tq-lime);
}

.nav-tabs a.active {
  font-weight: 700;
  border-bottom-color: var(--tq-lime);
}

.nav-motif {
  display: none;
  gap: 4px;
  margin-left: 0.75rem;
}

/* Only shown when the band has spare room */
@media (min-width: 1480px) {
  .nav-motif {
    display: flex;
  }
}

.nav-motif span {
  width: 14px;
  height: 14px;
}

.nav-motif span:nth-child(1) { background: var(--tq-navy-2); }
.nav-motif span:nth-child(2) { background: var(--tq-light-blue); }
.nav-motif span:nth-child(3) { background: var(--tq-lime); }
.nav-motif span:nth-child(4) { background: var(--tq-gold); }

/* Below ~1180px the tabs drop to their own row instead of overflowing */
@media (max-width: 1180px) {
  .logo {
    margin-right: auto;
  }

  .nav-container > .nav-tabs {
    order: 3;
    width: 100%;
    margin: 0;
    overflow-x: auto;
  }

  .nav-tabs a {
    padding-top: 0.625rem;
    padding-bottom: 0.5rem;
  }
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 2rem 3rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: var(--tq-text-muted);
  font-size: 1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

/* Cards are flat tint blocks: no border, no shadow */
.stat-card {
  background: var(--tq-tint);
  padding: 1.5rem;
}

.stat-label {
  color: var(--tq-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--tq-blue);
}

.stat-card.warning .stat-value {
  color: var(--warn);
}

.stat-card.success .stat-value {
  color: var(--ok);
}

.stat-card.danger .stat-value {
  color: var(--bad);
}

.stat-card.info .stat-value {
  color: var(--tq-light-blue);
}

.card {
  background: var(--tq-tint);
  padding: 1.75rem;
  margin-bottom: 1.5rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.card-title {
  font-size: 1.375rem;
  color: var(--tq-blue);
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  text-align: left;
  padding: 0.625rem 0.5rem;
  color: var(--tq-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--tq-border);
}

td {
  padding: 0.75rem 0.5rem;
  border-top: 1px solid var(--tq-border);
  color: var(--tq-blue);
  font-size: 0.875rem;
}

tbody tr:first-child td {
  border-top: none;
}

tbody tr:hover {
  background: var(--tq-bg);
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge.success,
.badge.increasing {
  background: var(--ok-bg);
  color: var(--ok);
}

.badge.warning,
.badge.medium {
  background: var(--warn-bg);
  color: var(--warn);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--bad-bg);
  color: var(--bad);
}

.badge.info,
.badge.low {
  background: var(--white);
  color: var(--tq-blue);
}

.badge.stable {
  background: var(--white);
  color: var(--tq-text-muted);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--tq-text-muted);
  font-size: 0.938rem;
}

.error {
  background: var(--bad-bg);
  color: var(--bad);
  padding: 1rem;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
