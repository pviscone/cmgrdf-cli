from CMGRDF import Plot

plots=[
    Plot("diele_mass_all", "DiElectron_mass", (30, 2.7, 3.3), xTitle = "Dielectron invariant mass, all pairs", includeOverflows=False),
    Plot("diele_mass_triggered", "diele_mass_triggered", (30, 2.7, 3.3), xTitle = "Dielectron invariant mass, trigger-matched", includeOverflows=False),
    Plot("diele_mass_PFPF", "diele_PFPF_mass", (30, 2.7, 3.3), xTitle = "Dielectron invariant mass, trigger-matched, PF + PF electrons", includeOverflows=False),
    Plot("diele_mass_LPPF", "diele_LPPF_mass", (30, 2.7, 3.3), xTitle = "Dielectron invariant mass, trigger-matched, LowPt + PF electrons", includeOverflows=False),
]