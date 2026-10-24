import { STORAGE_KEYS, STORAGE_NAMESPACE } from './state.js';
import { DRAFT_PICKS_STORAGE_KEY, DRAFT_PICKS_STORAGE_NAMESPACE } from './draftPicks.js';

export const DEPTH_CHART_STORAGE_CONTROLS = Object.freeze({
  namespace: STORAGE_NAMESPACE,
  keys: Object.freeze(Object.values(STORAGE_KEYS)),
  title: 'Depth Chart',
});

export const SHARED_DRAFT_PICKS_STORAGE_CONTROLS = Object.freeze({
  namespace: DRAFT_PICKS_STORAGE_NAMESPACE,
  keys: Object.freeze([DRAFT_PICKS_STORAGE_KEY]),
  title: 'Draft Picks Shared with Roster Cap',
});
