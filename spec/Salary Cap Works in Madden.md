# How the Salary Cap Works in Madden: Complete Guide

## Overview

The salary cap in Madden Franchise Mode simulates the NFL's real-world financial system, requiring strategic management of player contracts, guaranteed money, and cap penalties. Understanding these mechanics is essential for building a sustainable, competitive team.

---

## Core Salary Cap Concepts

### 1. Contract Structure

Every player contract in Madden consists of two primary components:

#### **Base Salary** (`contractSalary`)
* Total contract value paid over the length of the deal
* Distributed unevenly across contract years (escalating structure)
* Only counts against the cap in years the player is on your roster
* **Key point:** If you trade/cut a player, you stop paying their base salary

#### **Signing Bonus** (`contractBonus`)
* Guaranteed money paid to the player upfront (in real NFL terms)
* Spread evenly across the **first 5 years only** of the contract
* **Always counts against your cap**, even if player is traded/cut
* Creates "dead money" when players leave early

---

## Annual Cap Hit Calculation

### Formula
```
Annual Cap Hit = (Base Salary for that year) + (Signing Bonus ÷ Contract Length*)
```
*Maximum 5 years for bonus proration

### Contract Year Salary Distribution

Madden uses fixed percentages for base salary distribution across contract lengths:

#### **7-Year Contract Example**
*Base Salary: $80M | Signing Bonus: $60M*

| Year | Salary % | Salary Amount | Bonus/Year | Total Cap Hit |
|:---|:---|:---|:---|:---|
| 1 | 12,3% | $9 850 000 | $12 000 000 | $21 850 000 |
| 2 | 12,9% | $10 320 000 | $12 000 000 | $22 320 000 |
| 3 | 13,5% | $10 800 000 | $12 000 000 | $22 800 000 |
| 4 | 14,2% | $11 360 000 | $12 000 000 | $23 360 000 |
| 5 | 14,9% | $11 920 000 | $12 000 000 | $23 920 000 |
| 6 | 15,7% | $12 560 000 | $0 | $12 560 000 |
| 7 | 16,5% | $13 200 000 | $0 | $13 200 000 |

**Note:** Years 6-7 have no bonus because signing bonuses only prorate over 5 years maximum.

#### **6-Year Contract**
| Year | Salary % | Bonus/Year |
|:---|:---|:---|
| 1 | 14,7% | $12 000 000 |
| 2 | 15,4% | $12 000 000 |
| 3 | 16,2% | $12 000 000 |
| 4 | 17,0% | $12 000 000 |
| 5 | 17,9% | $12 000 000 |
| 6 | 18,8% | $0 |

#### **5-Year Contract**
| Year | Salary % | Bonus/Year |
|:---|:---|:---|
| 1 | 18,0% | $12 000 000 |
| 2 | 19,0% | $12 000 000 |
| 3 | 20,0% | $12 000 000 |
| 4 | 21,0% | $12 000 000 |
| 5 | 22,0% | $12 000 000 |

#### **4-Year Contract**
| Year | Salary % | Bonus/Year |
|:---|:---|:---|
| 1 | 23,2% | $15 000 000 |
| 2 | 24,3% | $15 000 000 |
| 3 | 25,5% | $15 000 000 |
| 4 | 27,0% | $15 000 000 |

#### **3-Year Contract**
| Year | Salary % | Bonus/Year |
|:---|:---|:---|
| 1 | 31,7% | $20 000 000 |
| 2 | 33,3% | $20 000 000 |
| 3 | 35,0% | $20 000 000 |

#### **2-Year Contract**
| Year | Salary % | Bonus/Year |
|:---|:---|:---|
| 1 | 48,7% | $30 000 000 |
| 2 | 51,3% | $30 000 000 |

---

## Dead Money & Cap Penalties

### What is Dead Money?

**Dead money** (`capReleasePenalty`) is the remaining guaranteed money (signing bonus) that accelerates to your cap when you cut or trade a player.

### How Cap Penalties Work

#### **Rule 1: Multi-Year Contracts (2+ years remaining)**
When you cut/trade a player with 2+ years left:
* **Current Year Penalty:** ~60% of remaining bonus
* **Next Year Penalty:** ~40% of remaining bonus

Note: Some CSV exports label “Penalty Year 1/Year 2” opposite of in‑game application. In practice, the value labeled “Year 2” applies to the current season, and “Year 1” applies to the following season. Our tools normalize this by applying the 60/40 split as described.

**Example:**
* Player has $40M signing bonus on 4-year deal
* Bonus = $10M/year for 4 years
* You cut him after Year 1
* **Remaining bonus:** $30M ($10M × 3 years)
* **Current year penalty:** ~$18M
* **Next year penalty:** ~$12M

#### **Rule 2: Final Year of Contract**
* **All remaining bonus hits current year only**
* No future year penalty

#### **Rule 3: Five-Year Maximum**
* Signing bonuses only apply to first 5 years
* Years 6-7 have **zero dead money risk**
* Cutting a player in Year 6+ = no cap penalty from that contract

---

## Team Salary Cap Dashboard

### Understanding the Salaries Page

When you navigate to **Manage Roster → Team Salaries**, you'll see critical financial metrics:

#### **Top Row (Left to Right)**

| Metric | Description |
|:---|:---|
| **2024 Cap** (`capRoom`) | League-wide salary cap (e.g., $304 200 000) |
| **Rollover from 2023** | Unused cap space from previous season |
| **Adjusted Cap** | Current Cap + Rollover = Total available |
| **Cap Space** (`capAvailable`) | Money remaining after all spending |

#### **Bottom Row (Left to Right)**

| Metric | Description |
|:---|:---|
| **2024 Salaries** | Total base salaries for active roster |
| **Cap Penalty** | Dead money from cut/traded players |
| **Total Spending** (`capSpent`) | Salaries + Penalties = Total cap charge |
| **Rookie Reserve** | Projected cost of upcoming draft class |

### Critical Formula
```
Cap Space = Adjusted Cap - Total Spending
```

**Example (Vikings):**
* Adjusted Cap: $262 000 000
* Salaries: $182 000 000
* Cap Penalty: $57 400 000
* **Total Spending:** $239 400 000
* **Cap Space:** $22 600 000

---

## Trading & Salary Cap Mechanics

### Key Rule: **You Keep the Dead Money**

When you trade a player:
* **Receiving team:** Pays base salary only
* **Trading team:** Eats all remaining signing bonus as dead money

### Trade Example

**Scenario:** Trade McGlinchey ($8M salary, $8.8M bonus remaining) for Becton ($500K salary)

**Result:**
* You **save** $8M in salary
* You **lose** $8.8M in dead money acceleration
* **Net cap impact:** -$800K (you're worse off this year)

### Before Trading: Check These Fields

| Field | What It Means |
|:---|:---|
| `capReleaseNetSavings` | Cap space you'll **gain** this year |
| `capReleasePenalty` | Dead money you'll **owe** (split over 1-2 years) |
| **Savings** (in-game column) | Net gain/loss for current season |

**Pro Tip:** Sort by "Savings" column to find players you can cut/trade for **positive** cap relief.

---

## Rollover Cap: The Double-Edged Sword

### How Rollover Works

* Unused cap space from Season X carries over to Season X+1
* **Maximum rollover:** All unused cap (no limit in Madden)
* Adds to your "Adjusted Cap" next season

### The Trap

**Scenario:**
1. You have $20M cap space at end of 2024
2. 2025 cap increases by $15M (to $270M)
3. Your adjusted 2025 cap = $270M + $20M rollover = $290M
4. You spend all $290M on contracts
5. 2026 cap only increases to $285M
6. **You're now $5M over the cap before the season starts**

### Best Practice
* **Don't rely on rollover for long-term spending**
* Use rollover for one-time signings or emergencies
* Always leave 5-10% cap buffer

---

## Rookie Reserve & Draft Picks

### What is Rookie Reserve?

The **projected cost** of your draft class based on:
* Number of draft picks
* Draft position of each pick
* League salary scale for rookies

### Important Notes

* **Not included in current cap space display**
* Hits your cap **after** the draft when you sign rookies
* Can range from $7M (3 picks) to $30M+ (10+ picks with high selections)

### Example

**Vikings:** 3 picks (1st, 5th, 5th) = $7M rookie reserve  
**Chargers:** 9 picks (two 1sts, two 2nds, etc.) = $28.9M rookie reserve

### Cap Space Trap

**Scenario:**
* You have $22M cap space
* Your rookie reserve is $25M
* **After draft:** You're -$3M over the cap

**Solution:** Always subtract rookie reserve from cap space when planning signings.

---

## Contract Restructuring

### What is Restructuring?

Converting current-year base salary into signing bonus, spreading it over future years.

### How It Works

**Original Contract:**
* Year 1: $20M salary
* Year 2: $20M salary
* Year 3: $20M salary

**After Restructure:**
* Year 1: $5M salary + $5M bonus = $10M cap hit (saved $10M)
* Year 2: $20M salary + $5M bonus = $25M cap hit
* Year 3: $20M salary + $5M bonus = $25M cap hit

### When to Restructure

✅ **Good situations:**
* You need immediate cap space
* Player is a core piece for 3+ years
* You have future cap flexibility

❌ **Bad situations:**
* Player is aging or injury-prone
* You might trade/cut them soon (increases dead money)
* You're already tight on future cap

---

## Free Agent Signing Strategy

### Understanding Player Demands

Free agents have three demands:
* `desiredSalary` – Annual salary request
* `desiredBonus` – Signing bonus request
* `desiredLength` – Contract years requested

### Negotiation Tips

1. **Meet 90%+ of demands** for acceptance
2. **Longer contracts = lower annual cap hit** (but more risk)
3. **Minimize signing bonus** to reduce future dead money
4. **Sign after Week 1 of preseason** for veteran minimum deals

### Cap Hit Calculation for Offers

```
Year 1 Cap Hit = Salary + (Bonus ÷ MIN(Length, 5))
```

**Example Offer:**
* 4 years, $12M/year salary, $20M bonus
* Year 1 Cap Hit = $12M + ($20M ÷ 4) = $17M

---

## Advanced Cap Management Strategies

### 1. The "Year 6-7 Strategy"

**Concept:** Sign aging stars (27-28 years old) to 7-year deals.

**Why it works:**
* Years 1-5: Manageable cap hits with bonus
* Years 6-7: No bonus, lower cap hit
* Player likely retires before Year 7
* **If they retire: No dead money penalty**

**Example:**
* Sign 28-year-old OL to 7yr/$70M deal, $35M bonus
* Years 1-5: ~$17M cap hit
* Years 6-7: ~$8M cap hit
* Retires at 34: Contract disappears, no penalty

### 2. Trade Away "Last Year" Contracts

**Concept:** Trade players in final contract year.

**Why it works:**
* Minimal/zero signing bonus remaining
* Receiving team gets 1 year of control
* You avoid paying big extension
* No dead money penalty

**Target players:**
* `contractYearsLeft = 1`
* High `capHit` but low `capReleasePenalty`

### 3. The Draft-and-Develop Model

**Concept:** Build through draft, avoid expensive free agents.

**Strategy:**
* Keep 2-3 offensive stars (QB, WR1, OL)
* Keep 2-3 defensive stars (EDGE, CB1, MLB)
* Fill 10+ roster spots with rookies on 5-7 year deals (75-78 OVR)
* Trade aging stars before final year
* Maintain $30M+ cap space cushion

**Benefits:**
* Rookie contracts are cheap
* Predictable cap structure
* Sustainable for 10+ seasons

### 4. Clearing Dead Money (Offline Franchise)

**Method:**
1. Go to **League** → **Members**
2. Select your team
3. Choose **"Clear Cap Penalties"**
4. Removes all dead money instantly

**When to use:**
* Inherited team with bad contracts
* Simulating a "new ownership" scenario
* You want to focus on gameplay, not cap management

---

## Common Salary Cap Mistakes

### ❌ Mistake #1: Ignoring Cap Penalties Before Trading

**Problem:** Trading high-bonus players without checking `capReleasePenalty`

**Example:**
* Trade WR with $30M bonus remaining
* Gain $8M in salary relief
* **Lose $30M to dead money**
* Net: -$22M cap space

**Solution:** Always check "Savings" column first.

---

### ❌ Mistake #2: Spending All Rollover Cap

**Problem:** Treating rollover as permanent cap increase

**Example:**
* 2024: $20M rollover + $255M cap = $275M adjusted
* Spend all $275M
* 2025: Cap only increases to $270M
* **You're $5M over before season starts**

**Solution:** Treat rollover as one-time bonus, not recurring.

---

### ❌ Mistake #3: Forgetting Rookie Reserve

**Problem:** Not accounting for draft class costs

**Example:**
* You have $15M cap space
* Draft 8 players (including 2 first-rounders)
* Rookie reserve: $18M
* **Post-draft: -$3M cap space**

**Solution:** Subtract rookie reserve from cap space before free agency.

---

### ❌ Mistake #4: Over-Restructuring Contracts

**Problem:** Pushing too much money into future years

**Example:**
* Restructure QB, WR, DE contracts in Year 1
* Years 2-3: All have inflated cap hits
* Can't afford to re-sign other players
* **Cap hell for 3+ seasons**

**Solution:** Restructure sparingly, only for core players.

---

### ❌ Mistake #5: Signing Big Contracts to Injury-Prone Players

**Problem:** High dead money risk if player declines

**Example:**
* Sign 30-year-old RB to 5yr/$50M, $25M bonus
* Year 2: Injury drops OVR from 88 → 79
* Cut him: $20M dead money penalty

**Solution:** Avoid long deals with high bonuses for:
* Players 30+ years old
* Injury-prone positions (RB, LB)
* Players with declining stats

---

## Salary Cap Quick Reference

### Key Fields Summary

| Field | What It Means | Where to Find |
|:---|:---|:---|
| `capHit` | Current year cap charge | Player card |
| `capReleaseNetSavings` | Cap space gained if cut | Salaries page |
| `capReleasePenalty` | Dead money if cut/traded | Salaries page |
| `contractSalary` | Total base salary | Player card |
| `contractBonus` | Total guaranteed money | Player card |
| `contractLength` | Years on contract | Player card |
| `contractYearsLeft` | Remaining years | Player card |
| `capRoom` | League salary cap | Team Salaries page |
| `capAvailable` | Your remaining cap space | Team Salaries page |
| `capSpent` | Total committed money | Team Salaries page |

### Cap Penalty Rules

| Situation | Penalty Structure |
|:---|:---|
| 2+ years remaining | 40% Year 1, 60% Year 2 |
| Final year remaining | 100% current year |
| Years 6-7 of contract | No penalty (bonus already paid) |
| Player retires | No penalty (contract voided) |
| Trade player | Same as cutting (you keep dead money) |

### Contract Length Strategies

| Length | Best For | Risk Level |
|:---|:---|:---|
| 1-2 years | Veterans, stop-gaps | Low |
| 3-4 years | Prime players (25-28) | Medium |
| 5 years | Young stars (22-25) | Medium |
| 6-7 years | Core franchise players | High (but Years 6-7 are safe) |

---

## Step-by-Step: Evaluating a Trade

**Question:** Should I trade this player?

### Step 1: Check Contract Details
* Go to **Manage Roster → Team Salaries**
* Find the player

### Step 2: Review Key Numbers
* **Savings:** Will I gain or lose cap space this year?
* **Penalty:** How much dead money will I owe?
* **Years Left:** Is this the last year? (Minimal penalty)

### Step 3: Calculate Net Impact
```
Net Cap Impact = Savings - (Penalty ÷ 2*)
```
*Penalty split over 2 years if 2+ years remaining

### Step 4: Decision Matrix

| Savings | Penalty | Decision |
|:---|:---|:---|
| Positive | Low (<$5M) | ✅ Safe to trade |
| Positive | High (>$10M) | ⚠️ Only if desperate for cap |
| Negative | Any amount | ❌ Keep player or wait |

---

## Conclusion

Mastering Madden's salary cap requires understanding:

1. **Contract structure** – Salary vs. bonus
2. **Dead money mechanics** – When penalties hit
3. **Rollover cap risks** – Don't overspend
4. **Rookie reserve** – Plan for draft costs
5. **Strategic restructuring** – Push money carefully
6. **Long-term planning** – Years 6-7 are golden

**Golden Rule:** Always check `capReleaseNetSavings` and `capReleasePenalty` before cutting or trading players. These two numbers determine whether a move helps or hurts your cap situation.

With disciplined cap management, you can build a dynasty that remains competitive for 10+ seasons without ever going into cap hell.
