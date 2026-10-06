import React, { useState } from 'react';
import { 
  Activity, Apple, Flame, ShoppingBag, ShieldCheck, 
  ChevronDown, ChevronUp, Copy, Check, Clock, Sparkles, 
  Terminal, Database, HeartPulse
} from 'lucide-react';

export default function NutritionSubsystemLedger() {
  const [openSection, setOpenSection] = useState(0);
  const [copiedRaw, setCopiedRaw] = useState(false);

  const toggleSection = (index) => {
    setOpenSection(openSection === index ? null : index);
  };

  const rawSourcePayload = {
    system_target: "Clinical Juice and Keto Subsystem",
    protocol_duration_days: 14,
    refeeding_duration_days: 4,
    hydration_base_total_cucumbers: 70,
    hydration_base_total_celery_bunches: 32,
    core_antioxidants: [
      "cyanidin-3-glucoside",
      "punicalagins",
      "betalains",
      "bromelain",
      "hesperidin",
      "naringin"
    ],
    viscosity_agents: [
      "organic_psyllium_husk",
      "milled_chia_seed",
      "acacia_senegal_gum"
    ],
    ketogenic_macronutrient_ratios: {
      fat_percentage: 75,
      protein_percentage: 20,
      carbohydrate_net_percentage: 5
    },
    electrolytes_target_mg_daily: {
      elemental_sodium: 5000,
      elemental_potassium: 1000,
      elemental_magnesium: 300
    }
  };

  const handleCopyPayload = () => {
    navigator.clipboard.writeText(JSON.stringify(rawSourcePayload, null, 2));
    setCopiedRaw(true);
    setTimeout(() => setCopiedRaw(false), 2000);
  };

  const ledgerData = [
    {
      id: "schedule-formulations",
      title: "1. DAILY JUICE SCHEDULE & HYBRID FORMULATIONS",
      badge: "5 Servings / Day",
      icon: Clock,
      content: (
        <div className="space-y-4 text-sm text-neutral-200">
          <p className="font-mono text-xs text-amber-400 bg-amber-950/30 p-2.5 rounded border border-amber-900/50">
            ENGINE WORKFLOW: Masticate base (40-80 RPM) &rarr; Transfer liquid to blender carafe &rarr; Introduce whole pigments + functional fiber &rarr; Pulse 25s &rarr; Consume &lt;300s.
          </p>
          <div className="overflow-x-auto rounded border border-neutral-800">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-neutral-850 text-neutral-300 font-mono text-xs uppercase border-b border-neutral-700">
                  <th className="p-3">Time</th>
                  <th className="p-3">Designation</th>
                  <th className="p-3">Cold-Press Mechanical Base</th>
                  <th className="p-3">Blender Suspension</th>
                  <th className="p-3">Biochemical Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800 text-xs font-sans">
                <tr className="hover:bg-neutral-900/60 transition-colors">
                  <td className="p-3 font-mono text-cyan-400 font-bold whitespace-nowrap">07:30</td>
                  <td className="p-3 font-semibold text-neutral-100">Anthocyanin Green Ignition</td>
                  <td className="p-3 text-neutral-300">1 English cucumber, 2 stalks Tuscan kale, 1 rib celery, 1/2 lemon</td>
                  <td className="p-3 text-neutral-300">1/2 cup wild blueberries, 1/4 cup blackberries, 1 tbsp milled chia</td>
                  <td className="p-3 text-neutral-400">Cyanidin-3-glucoside, chlorophyll, lutein; lipid-delayed fructose entry</td>
                </tr>
                <tr className="hover:bg-neutral-900/60 transition-colors">
                  <td className="p-3 font-mono text-rose-400 font-bold whitespace-nowrap">10:30</td>
                  <td className="p-3 font-semibold text-neutral-100">Betalain &amp; Nitric Surge</td>
                  <td className="p-3 text-neutral-300">1 red beet, 2 carrots, 1 in ginger root, 1 in turmeric root</td>
                  <td className="p-3 text-neutral-300">1/2 cup pomegranate arils, 1/2 cup red grapes, 1 tsp psyllium husk, cracked pepper</td>
                  <td className="p-3 text-neutral-400">Punicalagins, betanin, eNOS activation, piperine-assisted curcuminoid transport</td>
                </tr>
                <tr className="hover:bg-neutral-900/60 transition-colors">
                  <td className="p-3 font-mono text-emerald-400 font-bold whitespace-nowrap">13:30</td>
                  <td className="p-3 font-semibold text-neutral-100">Cruciferous Proteolytic Shield</td>
                  <td className="p-3 text-neutral-300">1/4 green cabbage head, 1 cup baby spinach, 1 English cucumber, 1 lime</td>
                  <td className="p-3 text-neutral-300">3/4 cup fresh pineapple (core intact), 2 tbsp virgin cucumber pulp</td>
                  <td className="p-3 text-neutral-400">Sulforaphane precursors, glucosinolates, proteolytic bromelain isolation</td>
                </tr>
                <tr className="hover:bg-neutral-900/60 transition-colors">
                  <td className="p-3 font-mono text-amber-400 font-bold whitespace-nowrap">16:30</td>
                  <td className="p-3 font-semibold text-neutral-100">Bioflavonoid Osmolyte Matrix</td>
                  <td className="p-3 text-neutral-300">1 ruby red grapefruit, 1/2 fennel bulb, 1 English cucumber</td>
                  <td className="p-3 text-neutral-300">1 blood orange (albedo pith retained), 1/3 cup diced mango, 5g acacia fiber</td>
                  <td className="p-3 text-neutral-400">Hesperidin, naringin, provitamin A carotenoids, cecal butyrate fuel</td>
                </tr>
                <tr className="hover:bg-neutral-900/60 transition-colors">
                  <td className="p-3 font-mono text-indigo-400 font-bold whitespace-nowrap">19:30</td>
                  <td className="p-3 font-semibold text-neutral-100">Nocturnal Mineral Restorative</td>
                  <td className="p-3 text-neutral-300">1 bunch Swiss chard, 1 English cucumber, 1/2 cup mint leaves, 1/2 lemon</td>
                  <td className="p-3 text-neutral-300">1/2 cup pitted tart cherries, 1 pinch pink Himalayan salt</td>
                  <td className="p-3 text-neutral-400">Proanthocyanidins, exogenous melatonin, baseline Na+/K+ replenishment</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )
    },
    {
      id: "procurement-matrix",
      title: "2. 14-DAY INVENTORY CONSOLIDATION & STAGGERED REQUISITION",
      badge: "4 Grocery Cadences",
      icon: ShoppingBag,
      content: (
        <div className="space-y-4 text-sm text-neutral-200">
          <p className="font-mono text-xs text-neutral-400">
            PROCUREMENT CADENCE: Requisition dry/frozen stocks on Phase Init. Split dynamic produce into 4 sequential acquisitions (Day 1, 4, 8, 11) to avoid cell wall collapse and chlorosis.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-neutral-800 p-4 bg-neutral-900/80 rounded-lg">
              <h4 className="font-mono text-xs uppercase tracking-wider text-emerald-400 mb-3 flex items-center gap-1.5 font-bold">
                <Apple size={14} /> Perishable Produce: Field Stocks
              </h4>
              <ul className="list-disc list-inside space-y-1.5 font-mono text-xs text-neutral-300">
                <li>English Cucumbers: 70 units (5/day)</li>
                <li>Celery: 32 bunches/heads (~9 ribs/day)</li>
                <li>Tuscan (Lacinato) Kale: 8 bunches</li>
                <li>Swiss Chard: 14 bunches (1 bunch/day)</li>
                <li>Dandelion Greens: 7 bunches (1 cup/day)</li>
                <li>Baby Spinach: 14 cups (~4 large 16oz tubs)</li>
                <li>Flat-Leaf Parsley / Mint / Cilantro: 7 bunches each</li>
                <li>Red Cabbage: 3 medium heads</li>
                <li>Green Cabbage: 2 medium heads</li>
                <li>Fennel Bulbs: 7 medium bulbs</li>
                <li>Red Beets: 14 units (1/day)</li>
                <li>Carrots: 42 medium (~10-12 lbs)</li>
                <li>Ginger Root: ~2.0 lbs bulk</li>
                <li>Turmeric Root: ~1.5 lbs bulk</li>
              </ul>
            </div>
            <div className="border border-neutral-800 p-4 bg-neutral-900/80 rounded-lg">
              <h4 className="font-mono text-xs uppercase tracking-wider text-amber-400 mb-3 flex items-center gap-1.5 font-bold">
                <Sparkles size={14} /> Fruit Stock &amp; Micro-Nutrients
              </h4>
              <ul className="list-disc list-inside space-y-1.5 font-mono text-xs text-neutral-300">
                <li>Meyer Lemons: 35 units</li>
                <li>Limes: 14 units</li>
                <li>Grapefruits: 14 units</li>
                <li>Blood Oranges: 14 units</li>
                <li>Whole Pineapples: 4 units (cores utilized)</li>
                <li>Pomegranates: 14 units (or 7 lbs arils)</li>
                <li>Red/Black Grapes: 7 lbs</li>
                <li>Wild Blueberries (Frozen): 7 lbs</li>
                <li>Blackberries (Frozen/Fresh): 7 half-pints</li>
                <li>Dark Tart Cherries (Frozen, Pitted): 7 lbs</li>
                <li>Mango Chunks (Frozen): 5 lbs</li>
                <li>Milled Chia Seeds: 1 lb bag</li>
                <li>Psyllium Husk (Whole): 1 lb container</li>
                <li>Acacia Fiber / Inulin: 250g powder</li>
                <li>Distilled White Vinegar: 2 gallons (Wash Base)</li>
              </ul>
            </div>
          </div>
        </div>
      )
    },
    {
      id: "preparation-tutorial",
      title: "3. EXTRACTION MECHANICS & EQUIPMENT SOP",
      badge: "Cold-Press & Shear",
      icon: Terminal,
      content: (
        <div className="space-y-3 font-mono text-xs text-neutral-200">
          <div className="p-3 border border-neutral-800 bg-neutral-900/70 rounded-lg">
            <span className="text-amber-400 font-bold">[STEP 01: STERILIZATION]</span> Submerge inventory in a 1:4 acetic acid (white vinegar) to tap water solution for 600 seconds. Degrades agrochemical binding agents and surface fungi. Retain epidermal layer on all carrots, beets, apples, and cucumbers. Remove citrus flavedo (outer zest) to eliminate severe limonin bitterness; retain internal albedo (white spongy pith).
          </div>
          <div className="p-3 border border-neutral-800 bg-neutral-900/70 rounded-lg">
            <span className="text-cyan-400 font-bold">[STEP 02: COMMINUTION]</span> Section fibrous stalks (celery, kale stems) into &lt;50mm cross-sections to eliminate long stringy fibers tangling the auger axis. Slice roots into uniform 25mm cubes.
          </div>
          <div className="p-3 border border-neutral-800 bg-neutral-900/70 rounded-lg">
            <span className="text-emerald-400 font-bold">[STEP 03: SLOW MASTICATION]</span> Run auger at 40-80 RPM. Feed sequence: 20% cucumber volume (lubricate screen) &rarr; dense greens/roots &rarr; 80% remaining high-water volume. Collect liquid yield.
          </div>
          <div className="p-3 border border-neutral-800 bg-neutral-900/70 rounded-lg">
            <span className="text-rose-400 font-bold">[STEP 04: EMULSIFICATION &amp; CONSUMPTION]</span> Deposit cold-press extract into blender. Add frozen/fresh whole fruit fractions and dry fiber (chia/psyllium/acacia). Execute mechanical shear for 25 seconds at medium velocity. Down immediately (&lt;3 minutes) prior to polysaccharide gelation.
          </div>
        </div>
      )
    },
    {
      id: "keto-snacks",
      title: "4. KETOGENIC COMPENSATORY SNACK PROTOCOLS (<3g NET CARBS)",
      badge: "<3g Net Carbs",
      icon: Flame,
      content: (
        <div className="overflow-x-auto text-sm text-neutral-200 rounded border border-neutral-800">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-neutral-850 text-neutral-300 font-mono text-xs uppercase border-b border-neutral-700">
                <th className="p-3 border-r border-neutral-800">Subsystem Item</th>
                <th className="p-3 border-r border-neutral-800">Stoichiometry (Ingredients)</th>
                <th className="p-3 border-r border-neutral-800">Preparation Process</th>
                <th className="p-3">Macronutrient Profile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800 text-xs font-sans">
              <tr className="hover:bg-neutral-900/60 transition-colors">
                <td className="p-3 font-semibold text-neutral-100 border-r border-neutral-800">Avocado-MCT Salt Pod</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">1 medium Hass Avocado, 1 tbsp Pure C8 MCT Oil, coarse sea salt, black pepper</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">Bisect pericarp, remove seed, inject C8 oil into central cavity, top with 1g NaCl. Eat with spoon.</td>
                <td className="p-3 font-mono text-emerald-400 font-semibold whitespace-nowrap">28g Fat | 3g Protein | 2g Net Carb</td>
              </tr>
              <tr className="hover:bg-neutral-900/60 transition-colors">
                <td className="p-3 font-semibold text-neutral-100 border-r border-neutral-800">Crisped Parmesan Seed Discs</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">1 cup aged Parmesan (micro-planed), 2 tbsp raw pepitas, 1 tbsp chia, 1/4 tsp smoked paprika</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">Form 50mm circles on parchment. Heat at 375&deg;F (190&deg;C) for 420s until maillard reactions appear. Cool 300s.</td>
                <td className="p-3 font-mono text-emerald-400 font-semibold whitespace-nowrap">18g Fat | 14g Protein | 1g Net Carb</td>
              </tr>
              <tr className="hover:bg-neutral-900/60 transition-colors">
                <td className="p-3 font-semibold text-neutral-100 border-r border-neutral-800">Macadamia Cacao Fat Cluster</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">1/2 cup Macadamia nut paste, 2 tbsp virgin coconut oil, 1 tbsp unsweetened cacao nibs</td>
                <td className="p-3 text-neutral-300 border-r border-neutral-800">Liquefy coconut oil, fold into paste with salt, transfer to silicone matrix, top with nibs, flash-freeze 1200s.</td>
                <td className="p-3 font-mono text-emerald-400 font-semibold whitespace-nowrap">22g Fat | 2g Protein | 1.5g Net Carb</td>
              </tr>
            </tbody>
          </table>
        </div>
      )
    },
    {
      id: "keto-meals",
      title: "5. HIGH-SATIETY KETOGENIC MEAL BLUEPRINTS",
      badge: "Mitochondrial Beta-Oxidation",
      icon: Activity,
      content: (
        <div className="space-y-4 text-sm text-neutral-200">
          <div className="p-4 border border-neutral-800 bg-neutral-900/80 rounded-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-2 mb-2">
              <h4 className="font-bold text-amber-400 text-base">MEAL 01: Wild Sockeye Filet with Charred Brassica in Tallow</h4>
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-900">
                45g Lipid | 38g Protein | 3g Net Carb
              </span>
            </div>
            <p className="text-xs leading-relaxed text-neutral-300">
              <strong>Execution:</strong> Sear 6 oz dry sockeye filet skin-down in 1 tbsp rendered grass-fed tallow for 240s in high-heat cast iron. Flip, cook for 120s. Extract to board. Drop 1.5 cups diced broccoli florets and 1 minced garlic clove into pan with 1 tbsp secondary tallow. Char aggressively at high heat for 200s. Deglaze surface with 15mL lemon juice. Pour lipid residue over protein.
            </p>
          </div>
          <div className="p-4 border border-neutral-800 bg-neutral-900/80 rounded-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-2 mb-2">
              <h4 className="font-bold text-amber-400 text-base">MEAL 02: Basted Prime Ribeye Strip with Garlic Butter Wilted Chard</h4>
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-900">
                55g Lipid | 42g Protein | 2g Net Carb
              </span>
            </div>
            <p className="text-xs leading-relaxed text-neutral-300">
              <strong>Execution:</strong> Temper 8 oz prime ribeye to 20&deg;C ambient. Salt heavily. Sear in dry cast iron smoking-hot for 150s per face. Drop 30g pasture-raised butter, crushed allium clove, and rosemary; arrose (spoon baste) continuously for 120s. Extract steak; allow 360s muscle relaxation. Drop 2 cups chopped Swiss chard into pan drippings. Sauté for 90s. Serve beneath sliced steak.
            </p>
          </div>
        </div>
      )
    },
    {
      id: "refeeding-protocol",
      title: "6. STEPPED REFEEDING & METABOLIC PHASE-SHIFT (DAYS 15-18)",
      badge: "Prevent Refeeding Syndrome",
      icon: ShieldCheck,
      content: (
        <div className="space-y-3 text-xs font-mono text-neutral-200">
          <div className="p-3 border-l-4 border-amber-500 bg-neutral-900/70 rounded-r-lg">
            <span className="text-amber-400 font-bold block mb-1">PHASE 01 (DAY 15 - ENZYME RESTORATION):</span>
            Maintain Juice 01 at 07:30. At 13:00 consume 350mL warm bovine bone broth with 5g salt and 1/2 mashed avocado. At 18:00 ingest steamed zucchini and puréed cauliflower with 15mL extra virgin olive oil. ZERO solid muscle meat.
          </div>
          <div className="p-3 border-l-4 border-amber-500 bg-neutral-900/70 rounded-r-lg">
            <span className="text-amber-400 font-bold block mb-1">PHASE 02 (DAY 16 - LIPID &amp; ALBUMIN ACCLIMATION):</span>
            Morning Juice 04. Midday meal: 2 poached pastured whole eggs with 1/2 sliced avocado and 250mL broth. Evening meal: 120g steamed white fish (halibut/cod) over wilted spinach in 15g grass-fed butter.
          </div>
          <div className="p-3 border-l-4 border-amber-500 bg-neutral-900/70 rounded-r-lg">
            <span className="text-amber-400 font-bold block mb-1">PHASE 03 (DAY 17 - SKELETAL MYOSIN INTEGRATION):</span>
            Morning: Avocado-MCT Salt Pod with black coffee. Midday: Sockeye Salmon Blueprint (Half Portion). Evening: 120g pasture-raised 80/20 ground beef browned in tallow over raw arugula with extra virgin olive oil.
          </div>
          <div className="p-3 border-l-4 border-emerald-500 bg-neutral-900/70 rounded-r-lg">
            <span className="text-emerald-400 font-bold block mb-1">PHASE 04 (DAY 18+ - HARD METABOLIC STATE TRANSITION):</span>
            Cut liquid sugars. Deploy full ketogenic macronutrient targets: 70-75% Lipid, 20-25% Protein, &lt;5% Net Carbohydrates. Maintain strict exogenous electrolytes: 5000mg Na+, 1000mg K+, 300mg Mg-glycinate daily to prevent aldosterone-induced natriuresis shock.
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="w-full max-w-6xl mx-auto bg-neutral-950 border border-neutral-800 rounded-xl p-5 md:p-8 font-sans text-neutral-100 shadow-2xl my-4">
      {/* Header Banner */}
      <div className="border-b border-neutral-800 pb-5 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <HeartPulse className="text-rose-500" size={22} />
            <span className="font-mono text-xs uppercase tracking-widest text-neutral-400">AI-BS Clinical Optimization Subsystem</span>
          </div>
          <h2 className="text-xl md:text-2xl font-mono font-bold tracking-tight text-white flex items-center gap-2">
            NUTRITIONAL RECONFIGURATION &amp; METABOLIC ENGINE
          </h2>
          <p className="text-xs font-mono text-neutral-400 mt-1">
            HYBRID COLD-PRESS MECHANICAL EXTRACTION &bull; POLYPHENOL EMULSIFICATION &bull; 4-DAY KETO REFEEDING
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyPayload}
            className="flex items-center gap-2 px-3 py-2 bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700 rounded-lg text-xs font-mono transition-colors"
          >
            {copiedRaw ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            <span>{copiedRaw ? 'Copied JSON Payload' : 'Export Subsystem JSON'}</span>
          </button>
        </div>
      </div>

      {/* Accordion Sections */}
      <div className="space-y-3">
        {ledgerData.map((section, idx) => {
          const isOpen = openSection === idx;
          const SectionIcon = section.icon;
          return (
            <div 
              key={section.id} 
              className={`border transition-all rounded-lg overflow-hidden ${
                isOpen ? 'border-amber-500/50 bg-neutral-900/60 shadow-lg' : 'border-neutral-800 bg-neutral-900/30 hover:border-neutral-700'
              }`}
            >
              <button
                onClick={() => toggleSection(idx)}
                className="w-full px-4 py-3.5 text-left font-mono text-xs uppercase tracking-wider flex justify-between items-center bg-neutral-850/50 hover:bg-neutral-800/60 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <SectionIcon size={16} className={isOpen ? 'text-amber-400' : 'text-neutral-400'} />
                  <span className="font-bold text-neutral-200">{section.title}</span>
                  {section.badge && (
                    <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] bg-neutral-800 text-neutral-400 rounded-full border border-neutral-700 font-sans">
                      {section.badge}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isOpen ? <ChevronUp size={16} className="text-amber-400" /> : <ChevronDown size={16} className="text-neutral-500" />}
                </div>
              </button>
              {isOpen && (
                <div className="p-4 md:p-6 bg-neutral-950/80 border-t border-neutral-800/80">
                  {section.content}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Forum Consensus Synthesis Card */}
      <div className="mt-6 p-4 border border-neutral-800 bg-neutral-900/40 rounded-lg">
        <h4 className="font-mono text-xs uppercase tracking-wider text-neutral-300 font-bold mb-2 flex items-center gap-2">
          <Database size={14} className="text-cyan-400" />
          Empirical Community Synthesis &amp; Biohacking Vault
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-neutral-400 font-sans">
          <div className="p-2.5 bg-neutral-950 rounded border border-neutral-800/60">
            <span className="font-bold text-neutral-200 block mb-1">r/juicing Consensus:</span>
            Reintroducing insoluble pulp (chia, psyllium, cucumber fibers) past Day 4 prevents hyperinsulinemia and acute biliary dumping.
          </div>
          <div className="p-2.5 bg-neutral-950 rounded border border-neutral-800/60">
            <span className="font-bold text-neutral-200 block mb-1">r/keto Transition:</span>
            Instantaneous shift to high fat causes dumping without 4-day enzymatic stepped refeeding; maintain 5,000mg sodium daily.
          </div>
          <div className="p-2.5 bg-neutral-950 rounded border border-neutral-800/60">
            <span className="font-bold text-neutral-200 block mb-1">Biohacking Metrics:</span>
            Fructose-heavy liquid protocols cause reactive hypoglycemia within 90m; chia ALA fats and psyllium stabilize metabolic curves.
          </div>
        </div>
      </div>
    </div>
  );
}
