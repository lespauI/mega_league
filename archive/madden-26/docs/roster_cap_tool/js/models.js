/**
 * @typedef {Object} Team
 * @property {string} abbrName
 * @property {string} displayName
 * @property {number} capRoom
 * @property {number} capSpent
 * @property {number} capAvailable
 * @property {number} seasonIndex
 * @property {number} weekIndex
 */

/**
 * @typedef {Object} Player
 * @property {string} id
 * @property {string} firstName
 * @property {string} lastName
 * @property {string} position
 * @property {number=} age
 * @property {string=} height
 * @property {number=} weight
 * @property {string=} team
 * @property {boolean} isFreeAgent
 * @property {number=} yearsPro
 * @property {number} capHit
 * @property {number=} capReleaseNetSavings
 * @property {number=} capReleasePenalty
 * @property {number=} contractSalary
 * @property {number=} contractBonus
 * @property {number=} contractLength
 * @property {number=} contractYearsLeft
 * @property {number=} desiredSalary
 * @property {number=} desiredBonus
 * @property {number=} desiredLength
 * @property {number=} reSignStatus
 * @property {boolean=} isOnIR
 */

/**
 * @typedef {Object} CapSnapshot
 * @property {number} capRoom
 * @property {number} capSpent
 * @property {number} capAvailable
 * @property {number} deadMoney
 * @property {number} baselineAvailable
 * @property {number} deltaAvailable
 */

/**
 * @typedef {{ type: 'release', playerId: string, penalty: number, savings: number, at: number, faYearsAtRelease?: number, freeOutYears?: number }} ReleaseMove
 * @typedef {{ type: 'tradeQuick', playerId: string, penalty: number, savings?: number, at: number, faYearsAtRelease?: number, freeOutYears?: number }} TradeQuickMove
 * @typedef {{ type: 'tradeIn', playerId: string, year1CapHit: number, at: number }} TradeInMove
 * @typedef {{ type: 'extend', playerId: string, years: number, salary: number, bonus: number, capHitDelta: number, at: number }} ExtensionMove
 * @typedef {{ type: 'convert', playerId: string, convertAmount: number, yearsRemaining: number, capHitDelta: number, at: number }} ConversionMove
 * @typedef {{ type: 'sign', playerId: string, years: number, salary: number, bonus: number, year1CapHit: number, at: number }} SignMove
 * @typedef {ReleaseMove | TradeQuickMove | TradeInMove | ExtensionMove | ConversionMove | SignMove} ScenarioMove
 */

/**
 * Scenario persistence (What-if mode)
 * Stores only the necessary diffs from baseline to keep payload small.
 * @typedef {Object} ScenarioRosterEdit
 * @property {string} id Player id
 * @property {{
 *   isFreeAgent?: boolean,
 *   team?: string,
 *   capHit?: number,
 *   contractSalary?: number,
 *   contractBonus?: number,
 *   contractLength?: number,
 *   contractYearsLeft?: number,
 * }} patch
 */

/**
 * @typedef {Object} Scenario
 * @property {string} id
 * @property {string} name
 * @property {string} teamAbbr
 * @property {number} savedAt
 * @property {number=} yearContextOffset Optional year context offset (default 0)
 * @property {Array<ScenarioMove>} moves
 * @property {Array<ScenarioRosterEdit>} rosterEdits
 */

export const __models = true;
