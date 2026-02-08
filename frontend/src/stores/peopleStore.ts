import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { Person, PeopleFilters } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface PeopleState {
  people: Person[];
  selectedPerson: Person | null;
  filters: PeopleFilters;
  total: number;
  isLoading: boolean;
  error: string | null;
}

interface PeopleActions {
  /** Fetch people with optional filters and pagination. */
  fetchPeople: (
    filters?: PeopleFilters,
    skip?: number,
    limit?: number,
  ) => Promise<void>;

  /** Fetch a single person by ID. */
  fetchPersonDetail: (personId: string) => Promise<void>;

  /** Submit COO corrections for a person record. */
  correctPerson: (
    personId: string,
    corrections: Partial<Person>,
  ) => Promise<void>;

  /** Trigger a full re-process / re-analysis of all people records. */
  reprocessPeople: () => Promise<void>;

  /** Update the local filter state (does not auto-fetch). */
  setFilters: (filters: PeopleFilters) => void;

  /** Set the selected person in local state. */
  setSelectedPerson: (person: Person | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type PeopleStore = PeopleState & PeopleActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const usePeopleStore = create<PeopleStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      people: [],
      selectedPerson: null,
      filters: {},
      total: 0,
      isLoading: false,
      error: null,

      // -- actions --

      fetchPeople: async (filters?, skip = 0, limit = 50) => {
        set({ isLoading: true, error: null }, false, "fetchPeople/start");
        try {
          const mergedFilters = filters ?? get().filters;
          const params: Record<string, string | number> = { skip, limit };

          if (mergedFilters.activity_level)
            params.activity_level = mergedFilters.activity_level;
          if (mergedFilters.department)
            params.department = mergedFilters.department;
          if (mergedFilters.project_id)
            params.project_id = mergedFilters.project_id;

          const { data } = await api.get<
            Person[] | { items: Person[]; total: number }
          >("/v1/people", { params });

          if (Array.isArray(data)) {
            set(
              { people: data, total: data.length, isLoading: false },
              false,
              "fetchPeople/success",
            );
          } else {
            set(
              {
                people: data.items,
                total: data.total,
                isLoading: false,
              },
              false,
              "fetchPeople/success",
            );
          }
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch people";
          set(
            { error: message, isLoading: false },
            false,
            "fetchPeople/error",
          );
          throw err;
        }
      },

      fetchPersonDetail: async (personId) => {
        set({ isLoading: true, error: null }, false, "fetchPersonDetail/start");
        try {
          const { data } = await api.get<Person>(`/v1/people/${personId}`);

          set(
            { selectedPerson: data, isLoading: false },
            false,
            "fetchPersonDetail/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch person details";
          set(
            { error: message, isLoading: false },
            false,
            "fetchPersonDetail/error",
          );
          throw err;
        }
      },

      correctPerson: async (personId, corrections) => {
        set({ isLoading: true, error: null }, false, "correctPerson/start");
        try {
          const { data } = await api.patch<Person>(
            `/v1/people/${personId}/correct`,
            corrections,
          );

          set(
            (s) => ({
              people: s.people.map((p) =>
                p.person_id === personId ? data : p,
              ),
              selectedPerson:
                s.selectedPerson?.person_id === personId
                  ? data
                  : s.selectedPerson,
              isLoading: false,
            }),
            false,
            "correctPerson/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to submit corrections";
          set(
            { error: message, isLoading: false },
            false,
            "correctPerson/error",
          );
          throw err;
        }
      },

      reprocessPeople: async () => {
        set({ isLoading: true, error: null }, false, "reprocessPeople/start");
        try {
          await api.post("/v1/people/reprocess");

          // Refetch people after reprocessing completes.
          await get().fetchPeople();
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to reprocess people records";
          set(
            { error: message, isLoading: false },
            false,
            "reprocessPeople/error",
          );
          throw err;
        }
      },

      setFilters: (filters) => {
        set({ filters }, false, "setFilters");
      },

      setSelectedPerson: (person) => {
        set({ selectedPerson: person }, false, "setSelectedPerson");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "PeopleStore" },
  ),
);
