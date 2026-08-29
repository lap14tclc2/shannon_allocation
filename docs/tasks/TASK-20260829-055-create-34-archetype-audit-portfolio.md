# TASK-20260829-055: Create 34 Economic Archetypes Audit Portfolio (68 Symbols)

- **ID**: `TASK-20260829-055`
- **Title**: Create 34 Economic Archetypes Audit Portfolio with Seeded Transactions
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
1. Create a dedicated audit portfolio (e.g. named `Audit 34 Archetypes Universe`) for user testing and engine regression.
2. Populate the portfolio with 1 BUY transaction per symbol across all 34 economic archetypes (2 symbols per archetype = 68 symbols).
3. Transaction specifications:
   - Price: default `10,000` VND per share.
   - Quantity: default `100` shares.
   - Broker / Security: `tcbs`.
   - Event type: `BUY`.
   - Initial cash deposit to maintain non-negative cash balance invariant.
4. Universe of 34 Archetypes (68 symbols):
   1. Commercial Bank: VCB, MBB
   2. Securities Broker: SSI, VCI
   3. Insurance: BVH, PVI
   4. Holding / Conglomerate: VEA, REE
   5. Residential Real Estate: VHM, NLG
   6. Industrial Real Estate / KCN: IDC, KBC
   7. Construction / EPC: CTD, FCN
   8. BOT / Concession Infrastructure: HHV, CII
   9. Steel / Metals: HPG, HSG
   10. Chemical / Fertilizer: DGC, DCM
   11. Cement / Building Materials: HT1, BCC
   12. Mining / Resources: KSV, MSR
   13. Oil & Gas Services: PVD, PVS
   14. Gas / Midstream Infrastructure: GAS, CNG
   15. Refining / Fuel Distribution: BSR, PLX
   16. Thermal / Gas Power: PPC, NT2
   17. Hydropower: VSH, CHP
   18. Renewable Power: GEG, PC1
   19. Water Utility: BWE, TDM
   20. Consumer Staples / Brand: VNM, MCH
   21. Retail Chain: MWG, FRT
   22. Consumer Discretionary: PNJ, HAX
   23. Technology / Software Services: FPT, CMG
   24. Telecom / Digital Infrastructure: CTR, VGI
   25. Pharmaceutical / Healthcare: DHG, TNH
   26. Port Infrastructure: GMD, VSC
   27. Logistics / Air Cargo: SCS, VTP
   28. Shipping: HAH, VOS
   29. Airline: VJC, HVN
   30. Airport Infrastructure / Services: ACV, AST
   31. Agriculture / Livestock: BAF, HAG
   32. Rubber Plantation / Land Bank: GVR, PHR
   33. Seafood / Aquaculture Export: VHC, FMC
   34. Textile / Garment Export: MSH, TCM

## Acceptance Criteria
- [x] Portfolio created under active users (`admin`, `alice`, `bob`).
- [x] 68 BUY ledger events appended with default price `10,000` VND, quantity `100`, broker `tcbs`.
- [x] Cash deposit added first to preserve non-negative cash balance ledger invariant.
- [x] Database verified with 68 distinct positions across all 34 archetypes.
- [x] Daily snapshots / sync recomputed for the new portfolio.
- [x] Responsive layout of `technical-summary` and `technical-content` on mobile screens fixed.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Ledger invariant preserved (`cash >= 0`).

## Implementation Tasks
- [x] 1. Write and execute portfolio creation script for 34 archetypes (68 symbols).
- [x] 2. Seed cash deposit + 68 BUY transactions with broker `tcbs` and price `10,000` VND.
- [x] 3. Run portfolio sync/recalculation to derive positions and portfolio state.
- [x] 4. Fix mobile broken layout of `.technical-summary` and `.valuation-technical-details` in `valuation-page.css`.

## Validation Evidence
1. **Database Ledger Seeding**:
   - `Audit 34 Archetypes Universe` created for users (`admin` ID 6, `alice` ID 4, `bob` ID 5).
   - 1 `CASH_DEPOSIT` (10 tỷ VND) + 68 `BUY` transactions recorded with broker `tcbs`, default price 10,000 VND / 100 shares.
   - Total transactions: 69, 68 positions across all 34 archetypes.
2. **Mobile CSS Fix**:
   - `.valuation-technical-details`, `.technical-summary`, `.technical-content`, `.sensitivity-matrix-container`, and `.history-10y-table-container` given explicit `box-sizing: border-box`, `max-width: 100%`, and horizontal touch scrolling.
3. **Build & Tests**:
   - Frontend build succeeded: `npm --prefix frontend run build` (vite v6.4.3 clean bundle).
   - 30 pytest unit and contract tests passed.

## Decisions
- Initial cash deposit of 10B VND inserted prior to BUY events to maintain ledger balance invariant.
- Mobile table overflow handled via dedicated touch scroll wrapper with min-width constraints.

## Result
Audit portfolio successfully seeded with 68 symbols across 34 archetypes. Mobile technical summary layout fixed.
