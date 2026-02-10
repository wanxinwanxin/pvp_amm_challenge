# Visual Specifications for PVP AMM Presentation

**Generated:** 2025-02-10
**Purpose:** Detailed specifications for all diagrams, charts, and visuals
**Tools:** draw.io, Figma, PowerPoint shapes, Python/Plotly charts

---

## Design Language

### Color Palette

**Primary Colors:**
- Deep Blue: `#1E3A8A` - Headers, titles
- Teal: `#14B8A6` - Highlights, "new" features
- Orange: `#F97316` - Warnings, emphasis
- Gray Scale: `#F3F4F6`, `#9CA3AF`, `#1F2937` - Body text, backgrounds

**Status Colors:**
- Success Green: `#10B981`
- Warning Yellow: `#F59E0B`
- Error Red: `#EF4444`
- Info Blue: `#3B82F6`

### Typography

**Headers:** Inter Bold, 28-32pt
**Subheaders:** Inter Semibold, 20-24pt
**Body:** Inter Regular, 16-18pt
**Code:** Fira Code, 14-16pt
**Captions:** Inter Regular, 12-14pt

### Icon Set

Use **Feather Icons** or **Font Awesome** for consistency:
- ⚔️ Competition: crossed swords
- 🏆 Winning: trophy
- 📊 Analytics: bar chart
- 🔀 Routing: git-merge
- 🌐 Platform: globe
- ⚙️ Settings: gear
- 💻 Code: terminal
- 📈 Growth: trending up

---

## Slide-by-Slide Visual Specifications

### Slide 2: Evolution Timeline

**Visual Type:** Horizontal timeline with comparison boxes

**Layout:**
```
2024 ←────────────────────→ 2026
[Original Box]    [Arrow]    [Modified Box]
```

**Original Box (Left):**
- Background: Light gray (#F3F4F6)
- Border: Gray (#9CA3AF), 2px
- Icons beside each bullet point
- Slightly faded appearance

**Modified Box (Right):**
- Background: Light teal (#CCFBF1)
- Border: Teal (#14B8A6), 3px
- Icons beside each bullet point
- Vibrant, prominent appearance

**Arrow:**
- Large rightward arrow between boxes
- Gradient from gray to teal
- Label: "Evolution"

**Tools:** PowerPoint shapes or Figma
**Dimensions:** 10" wide x 5" tall

---

### Slide 5: Realism Gap Table

**Visual Type:** Comparison table with status indicators

**Table Structure:**
| Real Markets | Original Challenge | Impact |
|--------------|-------------------|---------|
| ✅ Feature   | ❌ Limitation     | 🔴 Gap  |

**Styling:**
- Header row: Deep blue background (#1E3A8A), white text
- Alternating row colors: White, light gray (#F9FAFB)
- Status icons:
  - ✅ Green checkmark for real markets
  - ❌ Red X for original limitations
  - 🔴 Red circle for impact severity

**Quote Box Below:**
- Background: Light orange (#FFF7ED)
- Border-left: 4px orange (#F97316)
- Font: Italic, 18pt
- Icon: 💬 speech bubble

**Tools:** PowerPoint table + manual styling
**Dimensions:** Full slide width

---

### Slide 6: Five Changes Grid

**Visual Type:** 2x3 grid of change boxes

**Layout:**
```
[Change 1] [Change 2] [Change 3]
[Change 4] [Change 5]
```

**Each Box Contains:**
- Icon (top): Large (48x48px)
- Title: Bold, 20pt
- Old/New comparison: 2 lines
- Background: White with subtle shadow

**Styling:**
- Border: 2px solid teal (#14B8A6)
- Border-radius: 8px
- Shadow: 0px 4px 12px rgba(0,0,0,0.1)
- Padding: 16px

**Progressive Reveal:**
If presenting live, animate boxes appearing one by one (200ms delay between each)

**Tools:** PowerPoint grouped shapes
**Dimensions:** Each box 3" x 2.5"

---

### Slide 7: Head-to-Head Diagram

**Visual Type:** Before/after flow diagram

**Before (Left Side):**
```
┌──────────┐
│ Your     │
│ Strategy │
└────┬─────┘
     │ Single arrow down
     ▼
┌──────────┐
│ Baseline │
│ (30bps)  │
└────┬─────┘
     │
     ▼
  [Score]
```

**After (Right Side):**
```
┌──────────┐  ⇄  ┌──────────┐
│Strategy A│     │Strategy B│
└────┬─────┘     └────┬─────┘
     │               │
     └───────┬───────┘
             ▼
      [Win/Loss/Draw]
```

**Styling:**
- Boxes: Rounded rectangles, white fill, blue border
- Arrows: Bold, 3px width
- Before: Gray theme
- After: Teal/blue theme (vibrant)
- Double arrow (⇄): Emphasizes competition

**Tools:** draw.io or PowerPoint SmartArt
**Dimensions:** 8" wide x 4" tall

---

### Slide 8: Fee Tier Structure Graph

**Visual Type:** Step function chart

**Chart Type:** Line chart with steps (not smooth)

**Data Series:**
```python
# Example: 3-tier structure
x_values = [0, 100, 100, 1000, 1000, 2000]  # Trade size (X tokens)
y_values = [30, 30, 20, 20, 10, 10]        # Fee (basis points)
```

**Styling:**
- X-axis: "Trade Size (X tokens)", log scale optional
- Y-axis: "Fee (basis points)"
- Line: Teal (#14B8A6), 3px width
- Fill under curve: Light teal with 30% opacity
- Tier boundaries: Vertical dashed lines (#9CA3AF)
- Annotations: Label each tier with fee value

**Variants for Slide 12 (Strategy Types):**
1. **Whale Hunter:** 40bps → 15bps → 5bps
2. **Retail Specialist:** 25bps → 28bps → 35bps (inverted)
3. **Standard:** 30bps → 20bps → 10bps (baseline)

**Tools:** Python + Matplotlib/Plotly → export PNG
**Dimensions:** 6" wide x 4" tall
**Resolution:** 300 DPI for clarity

**Python Code:**
```python
import matplotlib.pyplot as plt

x = [0, 100, 100, 1000, 1000, 2000]
y = [30, 30, 20, 20, 10, 10]

plt.figure(figsize=(8, 5))
plt.step(x, y, where='post', linewidth=3, color='#14B8A6')
plt.fill_between(x, y, step='post', alpha=0.3, color='#14B8A6')
plt.xlabel('Trade Size (X tokens)', fontsize=14)
plt.ylabel('Fee (basis points)', fontsize=14)
plt.title('3-Tier Fee Structure', fontsize=16, fontweight='bold')
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('fee_tier_chart.png', dpi=300)
```

---

### Slide 9: Convergence Flowchart

**Visual Type:** Iterative algorithm flowchart

**Flow:**
```
START
  ↓
[Initial split using constant fees]
  ↓
[Iteration loop]
  ↓
[Estimate X outputs from Y inputs]
  ↓
[Compute effective fees at sizes]
  ↓
[Recompute split with effective fees]
  ↓
[Check convergence: Δ < 0.1%?]
  ↓ NO (loop back)
  ↓ YES
[Return final split]
  ↓
END
```

**Styling:**
- Start/End: Rounded pill shape, deep blue fill
- Process boxes: Rectangles, white fill, blue border
- Decision diamond: Orange border for emphasis
- Arrows: Solid for main flow, dashed for loop back
- Loop counter: "Iteration 1, 2, 3..." beside loop arrow

**Annotations:**
- Add timing: "~3ms per iteration"
- Add convergence rate: "95% converge in ≤3"

**Tools:** draw.io (flowchart template) or Lucidchart
**Dimensions:** 6" wide x 8" tall (vertical)

---

### Slide 10: CLI vs Web Platform

**Visual Type:** Before/after screenshot comparison

**Before (Left):**
- Screenshot of terminal with CLI output
- Black background, green text (retro terminal look)
- Minimal, dated appearance
- Border: Dashed gray

**After (Right):**
- Mockup of web platform (or actual screenshot if available)
- Modern UI with colors, charts, buttons
- Leaderboard table visible
- Interactive elements highlighted
- Border: Solid teal

**Layout:**
```
┌─────────────┐     ┌─────────────┐
│   CLI       │  →  │   Web App   │
│  (boring)   │     │   (modern)  │
└─────────────┘     └─────────────┘
```

**Tools:** Screenshots + editing in Figma or PowerPoint
**Dimensions:** Each panel 5" x 4"

---

### Slide 11: Realism Comparison Table

**Visual Type:** Feature comparison matrix with color coding

**Table Structure:**
| Dimension | Original | Modified | Real Markets |
|-----------|----------|----------|--------------|
| ...       | 🔴 Poor  | 🟢 Good  | 🟢 Target    |

**Color Coding:**
- 🔴 Red (40-60%): Original limitations
- 🟡 Yellow (60-80%): Partial coverage
- 🟢 Green (80-100%): Good coverage

**Star Ratings Below Table:**
```
Original:  ⭐⭐☆☆☆  (40%)
Modified:  ⭐⭐⭐⭐☆  (85%)
```

**Styling:**
- Header: Deep blue background
- Cells: Color-coded based on score
- Star icons: Large (24px), gold color
- Percentage in bold beside stars

**Tools:** PowerPoint table + conditional formatting
**Dimensions:** Full slide width

---

### Slide 12: Strategy Dimensions Comparison

**Visual Type:** Side-by-side dimension lists with expansion

**Layout:**
```
Original (3)          Modified (7)
┌───────────┐        ┌───────────┐
│ ✅ Dim 1  │        │ ✅ Dim 1  │
│ ✅ Dim 2  │        │ ✅ Dim 2  │
│ ⚠️  Dim 3 │        │ ✅ Dim 3  │
└───────────┘        │ ✅ Dim 4  │
                     │ ✅ Dim 5  │
                     │ ✅ Dim 6  │
                     │ ✅ Dim 7  │
                     └───────────┘
```

**Styling:**
- Original box: Smaller, gray tones
- Modified box: Larger, teal/blue tones
- New dimensions (4-7): Highlighted with bold + icon
- Arrow or bracket showing expansion

**Fee Structure Charts Below:**
- Show 3 small step-function charts
- One for each strategy archetype
- Aligned horizontally

**Tools:** PowerPoint shapes + embedded charts
**Dimensions:** Full slide

---

### Slide 13: Skill Trees

**Visual Type:** Tree diagram showing skill progression

**Original Tree (Left):**
```
      AMM Basics
         │
    ┌────┴────┐
  CFMM     Fee Impact
    │
Basic Logic
```

**Modified Tree (Right):**
```
      AMM Basics
         │
    ┌────┴────┬────────────┬──────────┐
  CFMM    Fee Impact   Adversarial  Tiered
    │                   Strategy    Pricing
Basic Logic              │            │
                    Multi-venue   Iterative
                     Routing      Optimization
                         │
                   Data-Driven
                     Tuning
```

**Styling:**
- Nodes: Circles (original) vs rounded rectangles (modified)
- Connections: Simple lines (original) vs bold branching (modified)
- New nodes: Teal color with ⭐ icon
- Original: 3 terminal nodes, Modified: 8 terminal nodes

**Tools:** draw.io mind map or PowerPoint SmartArt
**Dimensions:** 8" wide x 5" tall

---

### Slide 14: Test Pyramid

**Visual Type:** Pyramid chart with test categories

**Pyramid Layers (bottom to top):**
```
        ┌───────────┐
        │  Edge(14) │  ← Top: Specialized
    ┌───────────────┐
    │ Convergence(36)│  ← Middle-top
┌───────────────────────┐
│  Accounting(22)       │  ← Middle
│  Optimal(24)          │
│  No-Arb(23)           │  ← Middle-bottom
│  Determinism(17)      │
└───────────────────────┘
│ Symmetry(15)          │
│ Backward-Compat(25)   │  ← Base: Foundational
└───────────────────────┘
```

**Styling:**
- Each layer: Different shade of blue (lighter at top)
- Text: White, bold, with test count
- Total at base: "150+ Total Tests"
- CI/CD badges to the right

**Badges:**
```
✅ Python 3.10, 3.11, 3.12
✅ Coverage 93%
✅ CI < 5 min
✅ 100% Pass Rate
```

**Tools:** PowerPoint stacked shapes or Python + Matplotlib
**Dimensions:** 7" wide x 5" tall

---

### Slide 16: Strategy Archetype Fee Charts

**Visual Type:** Three side-by-side step-function charts

**Chart 1: Whale Hunter**
```
40bps │     ┌─────
      │     │
15bps │     │     ┌─────
      │     │     │
5bps  │     │     │     ┌─────
      └─────┴─────┴─────┴────→
        0   100  500  1000  Size
```

**Chart 2: Retail Specialist**
```
40bps │                 ┌─────
      │                 │
28bps │           ┌─────┘
      │           │
25bps │     ┌─────┘
      └─────┴─────┴─────┴────→
        0   100  500  1000  Size
```

**Chart 3: Adaptive Defender**
- Animated/dashed line showing dynamic adjustment
- Multiple overlapping lines for different conditions
- Color-coded: Green (good), Yellow (normal), Red (defensive)

**Styling:**
- Each chart: 2.5" wide x 2" tall
- Aligned horizontally with spacing
- Titles above each: Bold, 16pt
- Annotations: Target flow type

**Tools:** Python + Matplotlib → PNG export
**Dimensions:** Combined 8" wide x 2.5" tall

---

### Slide 17: Pitfall Boxes

**Visual Type:** 5 warning boxes with X marks

**Box Structure:**
```
┌────────────────────────────┐
│ ❌ Pitfall #1: Title       │
│                            │
│ Bad: [Description]         │
│ Problem: [Consequence]     │
│ Result: [Outcome]          │
│                            │
│ ✅ Fix: [Solution]         │
└────────────────────────────┘
```

**Styling:**
- Border: 2px solid orange (#F97316)
- Background: Light orange (#FFF7ED)
- X mark: Large (32px), red
- Fix section: Light green background (#F0FDF4)
- Checkmark: Green (#10B981)

**Layout:**
- Stack vertically or 2 columns
- Consistent height per box
- Spacing between boxes

**Tools:** PowerPoint text boxes + shapes
**Dimensions:** Each box 7" wide x 1.5" tall

---

### Slide 18: Key Takeaways

**Visual Type:** 5 numbered icon boxes

**Layout:**
```
[1] [2] [3]
[4] [5]
```

**Box Structure:**
- Large number in circle (top-left)
- Icon (top-right)
- Title: Bold, 18pt
- Bullet points below: 3-4 items

**Styling:**
- Border: 2px solid blue (#3B82F6)
- Background: White with subtle gradient
- Number circle: Deep blue background, white text
- Icons: 48x48px, teal color

**Bottom Quote:**
- Full-width box below grid
- Light blue background (#DBEAFE)
- Border-left: 5px solid blue
- Large italic text (20pt)

**Tools:** PowerPoint grouped shapes
**Dimensions:** Grid 8" x 4", quote 8" x 1.5"

---

### Slide 19: Action Timeline

**Visual Type:** Horizontal timeline with three phases

**Timeline Structure:**
```
This Week ─────→ 2 Weeks ─────→ Ongoing
   [1-3]            [4-5]          [6-7]
```

**Phase Boxes:**
- **This Week:** Green theme, 3 action items
- **2 Weeks:** Blue theme, 2 action items
- **Ongoing:** Purple theme, 2 action items

**Action Items:**
- Icon + Number (e.g., 📚 1)
- Bold title
- Sub-bullets with details
- Checkbox format

**Tools:** PowerPoint timeline + grouped shapes
**Dimensions:** Full slide width x 6" tall

---

## Chart Data Specifications

### Convergence Histogram

**Purpose:** Show distribution of iteration counts
**Slide:** Slide 9 (Change #4)

**Data:**
```python
iterations = [1, 2, 3, 4, 5]
percentage = [12.3, 48.7, 34.2, 4.5, 0.3]
```

**Chart Type:** Vertical bar chart

**Styling:**
- Bars: Teal (#14B8A6)
- X-axis: "Iterations to Converge"
- Y-axis: "Percentage of Cases (%)"
- Highlight bar for 2-3 iterations (majority)
- Annotation: "95% converge in ≤3"

**Tools:** Python + Plotly
**Code:**
```python
import plotly.graph_objects as go

fig = go.Figure(data=[
    go.Bar(x=iterations, y=percentage, marker_color='#14B8A6')
])
fig.update_layout(
    title='Convergence Distribution',
    xaxis_title='Iterations',
    yaxis_title='Percentage (%)',
    template='plotly_white'
)
fig.write_image('convergence_histogram.png', width=800, height=500)
```

---

### Win Rate Distribution

**Purpose:** Show spread of strategy performance
**Slide:** Context for Slide 15 (Strategy)

**Data:**
```python
win_rates = [0.25, 0.35, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
frequency = [2, 5, 8, 12, 15, 10, 6, 3, 1]
```

**Chart Type:** Histogram with normal curve overlay

**Styling:**
- Bars: Blue (#3B82F6), semi-transparent
- Curve: Orange (#F97316), dashed
- Threshold line: Green vertical line at 60%
- Annotation: "Target: 60%+ win rate"

---

## Icon and Image Assets Needed

### Icons (48x48px, SVG or PNG)
1. ⚔️ Crossed swords - Competition
2. 🏆 Trophy - Winning
3. 📊 Bar chart - Analytics
4. 🔀 Merge arrows - Routing
5. 🌐 Globe - Platform
6. 💻 Terminal - CLI
7. 📚 Books - Documentation
8. 🔍 Magnifying glass - Explore
9. 🧪 Test tube - Testing
10. 🎯 Target - Goals

### Logos
- Streamlit logo (for tech stack)
- Python logo
- Solidity logo
- Docker logo (optional)

### Screenshots
- CLI terminal output (create if needed)
- Web platform leaderboard (actual or mockup)
- Match result page (actual or mockup)

---

## Design Tool Recommendations

### For Diagrams
- **draw.io (free):** Flowcharts, org charts, timelines
- **Lucidchart:** Professional diagrams, collaboration
- **Figma (free tier):** UI mockups, component design

### For Charts
- **Python + Plotly/Matplotlib:** Data-driven charts, exportable
- **Excel/Google Sheets:** Quick charts, easy editing
- **Chart.js:** Interactive web charts (if web-based slides)

### For Slide Design
- **PowerPoint:** Familiar, widely compatible
- **Google Slides:** Collaboration, cloud-based
- **Keynote:** Mac users, beautiful animations

### For Icons
- **Feather Icons:** Clean, minimal, free
- **Font Awesome:** Comprehensive, widely used
- **Heroicons:** Modern, Tailwind-styled

---

## Accessibility Considerations

1. **Color Contrast:** Ensure 4.5:1 minimum contrast ratio
   - Test with WebAIM contrast checker
   - Don't rely on color alone for meaning

2. **Text Size:** Minimum 16pt for body text
   - Larger (20-24pt) for presentations

3. **Alt Text:** Provide descriptions for all visuals
   - Describe chart trends, not just "bar chart"

4. **Animation:** Keep minimal, avoid flashing
   - Use for emphasis, not decoration

---

## Export Specifications

### For Print
- Resolution: 300 DPI minimum
- Format: PDF (preserves vectors)
- Color space: RGB (for screens), CMYK (for print)

### For Digital Display
- Resolution: 1920x1080 (HD) or 3840x2160 (4K)
- Format: PNG (charts), SVG (diagrams), PPTX (slides)
- File size: < 5MB per slide for smooth loading

---

## End of Visual Specifications

**Total Visuals Specified:** 20+ unique visuals across 20 slides
**Tools Required:** PowerPoint/Figma, Python (charts), draw.io (diagrams)
**Estimated Design Time:** 4-6 hours for complete deck
