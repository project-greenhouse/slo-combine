import { defineStore } from 'pinia';
import { ref } from 'vue';
import { httpsCallable } from 'firebase/functions';
import { functions } from '../firebase/config';

export interface RosterItem {
  Name: string;
  HawkinID: string | null;
  SprintID: string | null;
  ProAgilID: string | null;
  ValorID: string | null;
  athlete_uid?: string | null; // Future-proofing for when we pull the DB UUID
  Email?: string | null;
  BirthDate?: string | null;
  Gender?: string | null;
  GradYear?: string | number | null;
  SchoolGrade?: string | number | null;
  HeightInches?: number | string | null;
  LimbDominance?: string | null;
  Sports?: string | null;
  Positions?: string | null;
  CurrentSchool?: string | null;
}

export const useAthleteStore = defineStore('athlete', () => {
  // State
  const roster = ref<RosterItem[]>([]);
  const selectedAthlete = ref<RosterItem | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const metrics = ref<any>(null); // State to hold the detailed Firestore records
  const metricsLoading = ref(false);
  const metricsCache = ref<Record<string, any>>({}); // Cache to make switching athletes instant
  let currentRequestId = 0; // Race condition lock

  // Actions
  const fetchRoster = async () => {
    if (roster.value.length > 0) return; // Prevent re-fetching if already loaded

    loading.value = true;
    error.value = null;

    try {
      const getRoster = httpsCallable(functions, 'get_roster');
      const result = await getRoster();
      const responseData = result.data as { status: string; data: RosterItem[], message?: string, traceback?: string };

      if (responseData.status === 'success') {
        roster.value = responseData.data;
      } else {
        error.value = responseData.message || 'Failed to load roster data.';
        console.error("Backend returned error:", responseData.message);
        if (responseData.traceback) {
          console.error("Backend Traceback:\n", responseData.traceback);
        }
      }
    } catch (err: any) {
      console.error("Error fetching roster:", err);
      error.value = err.message || 'An error occurred while fetching the roster.';
    } finally {
      loading.value = false;
    }
  };

  const forceRefreshRoster = async () => {
    roster.value = [];
    metricsCache.value = {};
    await fetchRoster();
  };

  const selectAthlete = async (athlete: RosterItem) => {
    selectedAthlete.value = athlete;
    await fetchAthleteMetrics(athlete);
  };

  const fetchAthleteMetrics = async (athlete: RosterItem) => {
    // 1. Clear old data immediately to prevent visual ghosting!
    metrics.value = null;

    if (!athlete.athlete_uid) return;
    
    // 2. Check if we already fetched this athlete's data
    if (metricsCache.value[athlete.athlete_uid]) {
      metrics.value = metricsCache.value[athlete.athlete_uid];
      return; // Instant load!
    }

    const requestId = ++currentRequestId;
    metricsLoading.value = true;
    
    try {
      const getMetrics = httpsCallable(functions, 'get_athlete_metrics');
      const result = await getMetrics({ athlete_uid: athlete.athlete_uid, Name: athlete.Name, HawkinID: athlete.HawkinID, ValorID: athlete.ValorID });
      const responseData = result.data as any;
      
      // Only update state if this is still the active athlete requested (prevents ghosting!)
      if (requestId === currentRequestId && responseData.status === 'success') {
        metrics.value = responseData.data;
        metricsCache.value[athlete.athlete_uid] = responseData.data; // Save to cache
      } else if (responseData.status === 'error') {
        console.error("Backend error fetching metrics:", responseData.message);
        if (responseData.traceback) console.error("Traceback:\n", responseData.traceback);
      }
    } catch (err) {
      console.error("Error fetching athlete metrics:", err);
    } finally {
      if (requestId === currentRequestId) {
        metricsLoading.value = false;
      }
    }
  };

  return {
    roster, selectedAthlete, loading, error, metrics, metricsLoading,
    fetchRoster, forceRefreshRoster, selectAthlete, fetchAthleteMetrics
  };
});