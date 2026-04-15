<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
import { collection, query, where, onSnapshot } from 'firebase/firestore';
import { db } from '../firebase/config';
import { useAthleteStore } from '../stores/athleteStore';

// ECharts imports
import { use } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers'; // SVG renderer is much more performant for Vue reactivity
import { BarChart, GaugeChart, ScatterChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';
import { useAuthStore } from '../stores/authStore';

use([SVGRenderer, BarChart, GaugeChart, ScatterChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent]);

const store = useAthleteStore();
const authStore = useAuthStore();

onMounted(async () => {
  await store.fetchRoster();
  
  // If user is an athlete, automatically force-select their own profile
  if (authStore.userRole === 'athlete' && authStore.athleteName) {
    const myProfile = store.roster.find(a => a.Name === authStore.athleteName);
    if (myProfile) {
      store.selectAthlete(myProfile);
    }
  }
});

const handleAthleteChange = (event: Event) => {
  const selectElement = event.target as HTMLSelectElement;
  const athleteName = selectElement.value;
  const athlete = store.roster.find(a => a.Name === athleteName);
  if (athlete) store.selectAthlete(athlete);
};

// --- Fetch the Latest Summary Note ---
const latestSummary = ref('');
let unsubscribe: (() => void) | null = null;

const fetchLatestSummary = () => {
  if (unsubscribe) {
    unsubscribe();
    unsubscribe = null;
  }
  latestSummary.value = '';
  
  if (store.selectedAthlete?.Name) {
    const q = query(
      collection(db, 'athlete_summaries'),
      where('athlete_name', '==', store.selectedAthlete.Name)
    );
    
    unsubscribe = onSnapshot(q, (snap) => {
      const comments = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as any));
      // Sort locally to avoid needing a Firestore composite index immediately
      comments.sort((a, b) => {
        const timeA = a.created_at?.toMillis ? a.created_at.toMillis() : new Date(a.created_at || 0).getTime();
        const timeB = b.created_at?.toMillis ? b.created_at.toMillis() : new Date(b.created_at || 0).getTime();
        return timeB - timeA; 
      });
      
      if (comments.length > 0) {
        latestSummary.value = comments[0].summary_html;
      }
    }, (error) => {
      console.error("Presentation View Snapshot Error:", error);
    });
  }
};

watch(() => store.selectedAthlete, fetchLatestSummary, { immediate: true });
onUnmounted(() => { if (unsubscribe) unsubscribe(); });

// --- Benchmark Toggle Logic ---
const compareMode = ref('allTime'); // 'combine' | 'allTime' | 'elite'

const getDisplayRank = (metricType: 'sprint40'|'proAgility'|'verticalJump'|'broadJump'|'fp_jump_height'|'fp_mrsi') => {
  const rawRank = store.metrics?.ranks?.[metricType];
  if (!rawRank) return '--';
  
  // Mocking the variation for the toggle until the backend returns all 3 distinct datasets
  if (compareMode.value === 'elite') return Math.max(1, Math.round(rawRank * 0.82)); 
  if (compareMode.value === 'combine') return Math.min(99, Math.round(rawRank * 1.08));
  return rawRank;
};

const fpCmjData = computed(() => store.metrics?.force_plate_cmj || []);
const fpMrData = computed(() => store.metrics?.force_plate_mr || []);

const hasValorData = computed(() => {
  const v = store.metrics?.valor;
  return v && (v.Shoulder > 0 || v.Ankle > 0 || v.Hip > 0);
});

const hasJumpData = computed(() => {
  return (store.metrics?.standing_vert?.length > 0) || (store.metrics?.broad_jump?.length > 0);
});

const hasSpeedData = computed(() => {
  return (store.metrics?.sprint40?.length > 0) || (store.metrics?.pro_agility?.length > 0);
});

// Rank Coloring Helper
const getRankClass = (val: number | null | undefined) => {
  if (!val) return 'hidden';
  if (val >= 75) return 'bg-code8-green/10 text-code8-green border-code8-green';
  if (val >= 25) return 'bg-code8-amber/10 text-yellow-600 border-code8-amber';
  return 'bg-code8-red/10 text-code8-red border-code8-red';
};

// --- ECharts Configurations ---
const jumpChartOption = computed(() => {
  const vert = store.metrics?.standing_vert?.[0]?.VerticalJump || 0;
  const broad = store.metrics?.broad_jump?.[0]?.BestBroadJump || 0;

  const getJumpBenchmark = (metric: 'vert' | 'broad') => {
    if (compareMode.value === 'elite') return metric === 'vert' ? 35 : 120;
    if (compareMode.value === 'allTime') return metric === 'vert' ? 28 : 105;
    return metric === 'vert' ? 24 : 95;
  };
  
  return {
    animationDuration: 400,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { show: false },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: [`Vertical Jump (in)\n⭐ ${getDisplayRank('verticalJump')}th Pct`, `Broad Jump (in)\n⭐ ${getDisplayRank('broadJump')}th Pct`], axisLine: { lineStyle: { color: '#9ca3af' } }, axisLabel: { color: '#374151', fontWeight: 'bold', lineHeight: 18 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } } },
    series: [{
      name: 'Athlete',
      data: [
        { value: vert, itemStyle: { color: '#00A651', borderRadius: [4, 4, 0, 0] } },
        { value: broad, itemStyle: { color: '#e1c173', borderRadius: [4, 4, 0, 0] } }
      ],
      type: 'bar',
      barWidth: '40%',
      label: { show: true, position: 'top', formatter: '{c}"', fontWeight: 'bold', color: '#374151' }
    },
    {
      name: 'Benchmark Target',
      type: 'scatter',
      symbol: 'rect', // Creates a clean dash/hash mark
      symbolSize: [60, 4], // 60px wide, 4px tall (horizontal dash)
      itemStyle: { color: '#1f2937', opacity: 0.35 },
      z: 10, // Ensure it draws on top of the bars
      label: { show: true, position: 'right', formatter: 'Target\n{c}"', color: '#6b7280', fontSize: 10, fontWeight: 'bold', lineHeight: 12 },
      data: [getJumpBenchmark('vert'), getJumpBenchmark('broad')]
    }]
  };
});

const speedChartOption = computed(() => {
  // Parse best Sprint 40
  const sprintRaw = store.metrics?.sprint40 || [];
  const sMap: Record<string, any> = {};
  sprintRaw.forEach((r: any) => {
    if (!r.Distance) return;
    if (!sMap[r.ActivityIdentifier]) sMap[r.ActivityIdentifier] = {};
    sMap[r.ActivityIdentifier][r.Distance] = Number(r.Total) || 0;
  });
  const bestSprint = Object.values(sMap).reduce((best: any, curr: any) => {
    if (!best || !best['40']) return curr;
    if (!curr['40']) return best;
    return curr['40'] < best['40'] ? curr : best;
  }, null);

  const s10 = bestSprint && bestSprint['10'] ? bestSprint['10'] : 0;
  const s40 = bestSprint && bestSprint['40'] ? bestSprint['40'] - s10 : 0;

  // Parse best Pro Agility
  const agilRaw = store.metrics?.pro_agility || [];
  const aMap: Record<string, any> = {};
  agilRaw.forEach((r: any) => {
    if (!r.Distance) return;
    if (!aMap[r.ActivityIdentifier]) aMap[r.ActivityIdentifier] = {};
    aMap[r.ActivityIdentifier][r.Distance] = Number(r.Total) || 0;
  });
  const bestAgil = Object.values(aMap).reduce((best: any, curr: any) => {
    if (!best || !best['20']) return curr;
    if (!curr['20']) return best;
    return curr['20'] < best['20'] ? curr : best;
  }, null);

  const a5 = bestAgil && bestAgil['5'] ? bestAgil['5'] : 0;
  const a10 = bestAgil && bestAgil['10'] ? bestAgil['10'] - a5 : 0;
  const a15 = bestAgil && bestAgil['15'] ? bestAgil['15'] - (a5 + a10) : 0;
  const a20 = bestAgil && bestAgil['20'] ? bestAgil['20'] - (a5 + a10 + a15) : 0;

  const getSpeedBenchmark = (metric: 'sprint' | 'agility') => {
    if (compareMode.value === 'elite') return metric === 'sprint' ? 4.5 : 4.2;
    if (compareMode.value === 'allTime') return metric === 'sprint' ? 4.8 : 4.5;
    return metric === 'sprint' ? 5.1 : 4.8;
  };

  return {
    animationDuration: 400,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (val: any) => (val ? val.toFixed(2) + 's' : '') },
    legend: {
      data: ['0-10 yd', '10-40 yd', '0-5 yd', '5-10 yd', '10-15 yd', '15-20 yd'],
      bottom: 0, icon: 'circle', itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 10, color: '#6b7280' }
    },
    grid: { left: '2%', right: '8%', bottom: '15%', top: '5%', containLabel: true },
    xAxis: { type: 'value', name: 'Time (s)', nameLocation: 'middle', nameGap: 25, splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
    yAxis: { type: 'category', data: [`Pro Agility\n⭐ ${getDisplayRank('proAgility')}th Pct`, `40 Yard Sprint\n⭐ ${getDisplayRank('sprint40')}th Pct`], axisLine: { lineStyle: { color: '#9ca3af' } }, axisLabel: { color: '#374151', fontWeight: 'bold', lineHeight: 18 } },
    series: [
      // Agility Splits
      { name: '0-5 yd', type: 'bar', stack: 'total', itemStyle: { color: '#efb51b' }, data: [a5 || null, null] },
      { name: '5-10 yd', type: 'bar', stack: 'total', itemStyle: { color: '#f5c04a' }, data: [a10 || null, null] },
      { name: '10-15 yd', type: 'bar', stack: 'total', itemStyle: { color: '#f9cb6d' }, data: [a15 || null, null] },
      { name: '15-20 yd', type: 'bar', stack: 'total', itemStyle: { color: '#fdd68e', borderRadius: [0, 4, 4, 0] }, data: [a20 || null, null] },
      // Sprint Splits
      { name: '0-10 yd', type: 'bar', stack: 'total', itemStyle: { color: '#de425b' }, data: [null, s10 || null] },
      { name: '10-40 yd', type: 'bar', stack: 'total', itemStyle: { color: '#ea715f', borderRadius: [0, 4, 4, 0] }, data: [null, s40 || null] },
      // Target Markers
      {
        name: 'Benchmark Target',
        type: 'scatter',
        symbol: 'rect',
        symbolSize: [4, 40], // 4px wide, 40px tall (vertical dash)
        itemStyle: { color: '#1f2937', opacity: 0.35 },
        z: 10,
        label: { show: true, position: 'top', formatter: 'Target\n{c}s', color: '#6b7280', fontSize: 10, fontWeight: 'bold', lineHeight: 12 },
        data: [ [getSpeedBenchmark('agility'), 0], [getSpeedBenchmark('sprint'), 1] ] // [x: time, y: category index]
      }
    ]
  };
});

// --- Gauge Chart Factory ---
const createGaugeOption = (title: string, value: number) => {
  let color = '#00A651'; // Green
  if (value < 70) color = '#FF4B4B'; // Red
  else if (value <= 85) color = '#FFC107'; // Amber

  return {
    series: [
      {
        type: 'gauge',
        startAngle: 180, endAngle: 0,
        min: 0, max: 100, splitNumber: 1,
        itemStyle: { color: color },
        progress: { show: true, roundCap: true, width: 14 }, // Revert to solid fill
        pointer: { show: false }, 
        axisLine: { roundCap: true, lineStyle: { width: 14, color: [[1, '#e5e7eb']] } }, // Clean gray track
        axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
        title: {
          show: true, offsetCenter: ['0%', '35%'], fontSize: 13, fontWeight: 'bold', color: '#6b7280' // Shifted down
        },
        detail: {
          fontSize: 38, offsetCenter: ['0%', '-10%'], valueAnimation: true, // Shifted up
          formatter: '{value}', color: 'inherit', fontWeight: '900'
        },
        data: [{ value: Math.round(value) || 0, name: title }]
      }
    ]
  };
};

// Valor Gauges
const shoulderGaugeOption = computed(() => createGaugeOption('Shoulder', store.metrics?.valor?.Shoulder || 0));
const ankleGaugeOption = computed(() => createGaugeOption('Ankle', store.metrics?.valor?.Ankle || 0));
const hipGaugeOption = computed(() => createGaugeOption('Hip Hinge', store.metrics?.valor?.Hip || 0));

const printReport = () => {
  window.print();
};

</script>

<template>
  <div class="max-w-5xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:justify-between md:items-end mb-8 border-b border-gray-200 pb-4">
      <div>
        <h1 class="text-4xl font-black text-code8-dark tracking-tight uppercase">{{ store.selectedAthlete?.Name || 'Athlete Presentation' }}</h1>
        <p class="text-gray-500 font-medium mt-1">Code 8 Performance Combine Report</p>
      </div>
      
      <div class="flex flex-col items-end gap-3 mt-4 md:mt-0 print:hidden">
        <div class="flex items-center gap-3">
          <button v-if="store.selectedAthlete && !store.metricsLoading" @click="printReport" class="px-4 py-2 bg-code8-dark text-white rounded-md font-semibold text-sm hover:bg-gray-800 transition-colors flex items-center gap-2 shadow-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
            Download PDF
          </button>
          <select v-if="store.roster.length > 0 && authStore.userRole !== 'athlete'" class="block w-64 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-code8-gold focus:border-code8-gold sm:text-sm rounded-md shadow-sm bg-white border" :value="store.selectedAthlete?.Name || ''" @change="handleAthleteChange">
            <option value="" disabled>-- Switch Athlete --</option>
            <option v-for="athlete in store.roster" :key="athlete.Name" :value="athlete.Name">{{ athlete.Name }}</option>
          </select>
        </div>
        <div class="flex bg-gray-100 p-1 rounded-lg border border-gray-200 shadow-sm text-sm">
          <button @click="compareMode = 'combine'" :class="['px-3 py-1.5 rounded-md font-semibold transition-colors', compareMode === 'combine' ? 'bg-white text-code8-dark shadow' : 'text-gray-500 hover:text-gray-700']">Current Combine</button>
          <button @click="compareMode = 'allTime'" :class="['px-3 py-1.5 rounded-md font-semibold transition-colors', compareMode === 'allTime' ? 'bg-white text-code8-dark shadow' : 'text-gray-500 hover:text-gray-700']">All-Time</button>
          <button @click="compareMode = 'elite'" :class="['px-3 py-1.5 rounded-md font-semibold transition-colors', compareMode === 'elite' ? 'bg-white text-code8-dark shadow' : 'text-gray-500 hover:text-gray-700']">Pro / Elite</button>
        </div>
      </div>
    </div>

    <div v-if="!store.selectedAthlete" class="text-center py-20 text-gray-500 font-medium">
      {{ authStore.userRole === 'athlete' ? 'Your profile is not linked or could not be found. Please contact your coach.' : 'Please select an athlete from the dropdown above to view their presentation.' }}
    </div>

    <!-- Loading State -->
    <div v-else-if="store.metricsLoading" class="flex flex-col items-center justify-center py-32 text-code8-gold">
      <svg class="animate-spin h-12 w-12 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="text-xl font-bold text-gray-700">Analyzing Athlete Data...</span>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-8 print:grid-cols-2 print:gap-6 print:text-sm">
      
      <!-- Movement Quality (Valor) -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center lg:col-span-2 print:col-span-2 print:shadow-none print:border-gray-200 print:p-4 print:break-inside-avoid">
        <h3 class="text-lg font-bold text-gray-800 mb-2 self-start">Movement Quality</h3>
        <div v-if="hasValorData" class="grid grid-cols-3 w-full max-w-3xl">
          <v-chart class="w-full h-48" :option="shoulderGaugeOption" :update-options="{ notMerge: true }" autoresize />
          <v-chart class="w-full h-48" :option="hipGaugeOption" :update-options="{ notMerge: true }" autoresize />
          <v-chart class="w-full h-48" :option="ankleGaugeOption" :update-options="{ notMerge: true }" autoresize />
        </div>
        <div v-else class="py-8 flex flex-col items-center text-gray-400">
          <span class="text-sm italic">No movement session data recorded for this athlete.</span>
        </div>
      </div>

      <!-- Visualizations -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center print:shadow-none print:border-gray-200 print:p-4 print:break-inside-avoid">
        <h3 class="text-lg font-bold text-gray-800 mb-4 self-start">Explosive Power</h3>
        <v-chart v-if="hasJumpData" class="w-full h-72" :option="jumpChartOption" :update-options="{ notMerge: true }" autoresize />
        <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400 w-full h-72 bg-gray-50/50 rounded-lg border border-dashed border-gray-200">
          <span class="text-sm italic">No jump data recorded.</span>
        </div>
      </div>

      <!-- Speed & Agility -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center print:shadow-none print:border-gray-200 print:p-4 print:break-inside-avoid">
        <h3 class="text-lg font-bold text-gray-800 mb-4 self-start">Speed & Agility Breakdown</h3>
        <v-chart v-if="hasSpeedData" class="w-full h-72" :option="speedChartOption" :update-options="{ notMerge: true }" autoresize />
        <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400 w-full h-72 bg-gray-50/50 rounded-lg border border-dashed border-gray-200">
          <span class="text-sm italic">No speed & agility data recorded.</span>
        </div>
      </div>

      <!-- Force Plate Metrics -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center lg:col-span-2 print:col-span-2 print:shadow-none print:border-gray-200 print:p-4 print:break-inside-avoid">
        <h3 class="text-lg font-bold text-gray-800 mb-4 self-start">Force Plate Metrics</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
          
          <!-- CMJ Table -->
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
              <span class="font-semibold text-sm text-gray-700">Countermovement Jump (CMJ)</span>
              <span :class="getRankClass(store.metrics?.ranks?.fp_jump_height)" class="text-[10px] px-2 py-0.5 rounded border font-bold">{{ compareMode === 'elite' ? 'Elite' : compareMode === 'allTime' ? 'All-Time' : 'Combine' }} Rank (Jump Ht): {{ getDisplayRank('fp_jump_height') }}th Pct</span>
            </div>
            <div class="p-4" v-if="fpCmjData.length === 0"><p class="text-sm text-gray-500 italic">No CMJ data available.</p></div>
            <table class="w-full text-sm text-left text-gray-600" v-else>
              <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                <tr>
                  <th class="px-4 py-2 font-medium">Jump Height</th>
                  <th class="px-4 py-2 font-medium">mRSI</th>
                  <th class="px-4 py-2 font-medium">Peak Rel. Power</th>
                  <th class="px-4 py-2 font-medium">Braking Asymm</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in fpCmjData" :key="'cmj-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                  <td class="px-4 py-2 font-mono text-gray-900 font-bold">{{ row['Jump Height (in)'] ? Number(row['Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                  <td class="px-4 py-2 font-mono text-gray-900">{{ row['mRSI'] ? Number(row['mRSI']).toFixed(2) : '--' }}</td>
                  <td class="px-4 py-2 font-mono text-gray-900">{{ row['Peak Rel Prop Power (W/kg)'] ? Number(row['Peak Rel Prop Power (W/kg)']).toFixed(2) + ' W/kg' : '--' }}</td>
                  <td class="px-4 py-2 font-mono text-gray-900">
                    {{ row['Braking Asymmetry'] !== null ? Math.abs(row['Braking Asymmetry']) + '% ' + (row['Braking Asymmetry'] < 0 ? 'L' : 'R') : '--' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- MR Table -->
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 border-b border-gray-200 font-semibold text-sm text-gray-700">Multi-Rebound (MR)</div>
            <div class="p-4" v-if="fpMrData.length === 0"><p class="text-sm text-gray-500 italic">No MR data available.</p></div>
            <table class="w-full text-sm text-left text-gray-600" v-else>
              <thead class="text-xs text-gray-400 uppercase bg-white border-b border-gray-100">
                <tr>
                  <th class="px-4 py-2 font-medium">Jumps</th>
                  <th class="px-3 py-2 font-medium">Avg Ht</th>
                  <th class="px-3 py-2 font-medium">Peak Ht</th>
                  <th class="px-3 py-2 font-medium">Avg RSI</th>
                  <th class="px-4 py-2 font-medium">Peak RSI</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in fpMrData" :key="'mr-'+idx" class="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                  <td class="px-4 py-2 font-mono text-gray-900">{{ row['Number of Jumps'] || '--' }}</td>
                  <td class="px-3 py-2 font-mono text-gray-900">{{ row['Avg Jump Height (in)'] ? Number(row['Avg Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                  <td class="px-3 py-2 font-mono text-gray-900 font-bold">{{ row['Peak Jump Height (in)'] ? Number(row['Peak Jump Height (in)']).toFixed(2) + '"' : '--' }}</td>
                  <td class="px-3 py-2 font-mono text-gray-900">{{ row['Avg RSI'] ? Number(row['Avg RSI']).toFixed(2) : '--' }}</td>
                  <td class="px-4 py-2 font-mono text-gray-900 font-bold">{{ row['Peak RSI'] ? Number(row['Peak RSI']).toFixed(2) : '--' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

        </div>
      </div>

      <!-- Latest Coach Summary -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 border-t-4 border-t-code8-gold lg:col-span-2 print:col-span-2 print:shadow-none print:border-t-4 print:border-gray-200 print:p-4 print:break-inside-avoid">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Coach's Actionable Feedback</h3>
        <div v-if="latestSummary" class="prose prose-sm max-w-none text-gray-700 leading-relaxed" v-html="latestSummary"></div>
        <div v-else class="text-gray-400 italic text-sm">No evaluation notes have been recorded yet.</div>
      </div>
    </div>
  </div>
</template>