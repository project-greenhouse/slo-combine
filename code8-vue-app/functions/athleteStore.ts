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
}

export const useAthleteStore = defineStore('athlete', () => {
  // State
  const roster = ref<RosterItem[]>([]);
  const selectedAthlete = ref<RosterItem | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Actions
  const fetchRoster = async () => {
    if (roster.value.length > 0) return; // Prevent re-fetching if already loaded

    loading.value = true;
    error.value = null;

    try {
      const getRoster = httpsCallable(functions, 'get_roster');
      const result = await getRoster();
      const responseData = result.data as { status: string; data: RosterItem[] };

      if (responseData.status === 'success') {
        roster.value = responseData.data;
      } else {
        error.value = 'Failed to load roster data.';
      }
    } catch (err: any) {
      console.error("Error fetching roster:", err);
      error.value = err.message || 'An error occurred while fetching the roster.';
    } finally {
      loading.value = false;
    }
  };

  const selectAthlete = (athlete: RosterItem) => {
    selectedAthlete.value = athlete;
  };

  return {
    roster, selectedAthlete, loading, error,
    fetchRoster, selectAthlete
  };
});