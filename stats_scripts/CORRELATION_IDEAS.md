# Additional Team Statistics Correlations

20 new interesting correlation graphs to reveal strategic insights beyond the current 14 implemented.

## 1. QB Protection vs Efficiency
**X-Axis:** `sack_rate` (Sacks per dropback %)  
**Y-Axis:** `qb_rating`  
**Insight:** Does better pass protection lead to better QB performance? Measures offensive line impact.

## 2. Defensive Turnover Creation vs Points
**X-Axis:** `def_ints_per_game` + `def_fum_rec` (Total takeaways)  
**Y-Axis:** `win_pct`  
**Insight:** How much do defensive turnovers correlate with winning? Defense wins championships?

## 3. Ball Security vs Winning
**X-Axis:** `pass_int_pct` + `rush_fum` (Combined turnover rate)  
**Y-Axis:** `win_pct`  
**Insight:** Teams that protect the ball win games. Measures offensive discipline.

## 4. Explosive Offense Philosophy
**X-Axis:** `pass_yds_per_att`  
**Y-Axis:** `rush_explosive_rate` (20+ yard runs %)  
**Insight:** Do teams with explosive passing also have explosive running? Or do they specialize?

## 5. Offensive Efficiency Balance
**X-Axis:** `pass_yds_per_att`  
**Y-Axis:** `rush_yds_per_att`  
**Insight:** Balanced efficiency vs specialized offense. Who's good at both? Who's one-dimensional?

## 6. Red Zone Scoring Proxy
**X-Axis:** `td_per_play` (Overall TD efficiency)  
**Y-Axis:** `win_pct`  
**Insight:** Finishing drives with TDs (not FGs) wins games. Measures red zone effectiveness.

## 7. Defensive Pressure Impact
**X-Axis:** `def_sacks_per_game`  
**Y-Axis:** `pass_comp_pct` (Opponent completion % proxy)  
**Insight:** Does pass rush force incompletions? Sacks vs coverage effectiveness.

## 8. Ball Control Strategy
**X-Axis:** `rush_att_per_game`  
**Y-Axis:** `pass_ints_per_game`  
**Insight:** Running teams protect the ball better. Time of possession = fewer turnovers.

## 9. Receiving Efficiency vs Volume
**X-Axis:** `rec_catches` (Total volume)  
**Y-Axis:** `rec_yds_per_catch`  
**Insight:** High-volume short passing vs low-volume deep passing. West Coast vs vertical.

## 10. QB Accuracy Under Pressure
**X-Axis:** `sack_rate` (Pressure frequency)  
**Y-Axis:** `pass_comp_pct`  
**Insight:** Can QBs maintain accuracy when facing pressure? Mental toughness test.

## 11. Fumble Recovery Luck
**X-Axis:** `def_forced_fum`  
**Y-Axis:** `def_fum_rec`  
**Insight:** Fumbles are 50/50 balls. Teams above trend = lucky, below = unlucky.

## 12. Receiving Corps Reliability
**X-Axis:** `rec_catches`  
**Y-Axis:** `drop_rate`  
**Insight:** Do high-volume receivers drop more passes? Fatigue vs concentration.

## 13. Defensive Playmaking
**X-Axis:** `def_deflections`  
**Y-Axis:** `def_ints`  
**Insight:** Creating INTs requires getting hands on the ball first. Coverage quality indicator.

## 14. Run Game Physicality
**X-Axis:** `rush_broken_tackles`  
**Y-Axis:** `rush_tds`  
**Insight:** Power runners break tackles AND score TDs. Physical dominance at goal line.

## 15. Special Teams Field Position
**X-Axis:** `punt_net_avg` + `kickoff_touchbacks`  
**Y-Axis:** `win_pct`  
**Insight:** Combined special teams impact on field position. Hidden yards win games.

## 16. Pass Protection Breakdown Rate
**X-Axis:** `pass_att_per_game` (Dropback volume)  
**Y-Axis:** `sacks_allowed_per_game`  
**Insight:** More dropbacks = more sacks? Pass-heavy fatigue on offensive line.

## 17. Defensive Tackle Efficiency
**X-Axis:** `def_tackles`  
**Y-Axis:** `def_sacks` + `def_ints` (Big plays)  
**Insight:** High tackle teams chase plays. Low tackle teams make big plays (disruptive defense).

## 18. Offensive Consistency
**X-Axis:** `yds_per_play` (Efficiency)  
**Y-Axis:** `explosive_plays_per_game` (Big plays)  
**Insight:** Consistent efficient offense vs boom-or-bust explosive offense.

## 19. Turnover Differential Components
**X-Axis:** `total_turnovers` (Giveaways)  
**Y-Axis:** `total_takeaways` (Takeaways)  
**Insight:** Breaking down turnover margin. Top-right = aggressive both ways. Bottom-left = conservative.

## 20. Receiving YAC Creation
**X-Axis:** `rec_yac_pct` (YAC %)  
**Y-Axis:** `rec_yds_per_catch` (Total Y/C)  
**Insight:** YAC from short passes vs downfield catches. Scheme design indicator.

---

## Implementation Priority

### High Value (Implement First)
1. **QB Protection vs Efficiency** - Clear cause/effect
2. **Ball Security vs Winning** - Fundamental winning formula
3. **Offensive Efficiency Balance** - Strategic philosophy indicator
4. **Fumble Recovery Luck** - Identifies lucky/unlucky teams
5. **Turnover Differential Components** - Decomposes most predictive stat

### Medium Value (Interesting Insights)
6-15. Various efficiency and style correlations

### Lower Value (Nice to Have)
16-20. Specialized or derivative metrics

---

## Notes for Implementation

- Some correlations may require **calculated fields** (e.g., combined special teams score)
- Consider adding **conference filters** to all new graphs
- **R² thresholds**: Strong (>0.5), Moderate (0.25-0.5), Weak (<0.25)
- Use **color coding**: Red = above trend (better), Blue = below trend (worse)
- Add **insight text** explaining what each quadrant means

## Future Enhancements

- **3D correlations**: Use size or color for 3rd dimension (e.g., wins)
- **Time-based filters**: First 8 games vs last 8 games to show trends
- **Player drill-down**: Click team logo to see contributing players
- **Preset buttons**: Quick filters for "Playoff Teams Only" or "Balanced Offenses"
