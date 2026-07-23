## Styling System

The MinerAI frontend uses **Tailwind CSS v4** as its primary styling framework, configured via the `@tailwindcss/vite` plugin in a Vite-based React application. The project leverages Tailwind's modern `@theme` directive for design token management rather than a separate `tailwind.config.js` file.

### Core Technology Stack
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite 6 with `@vitejs/plugin-react`
- **CSS Framework**: Tailwind CSS v4.1.14 (via `@tailwindcss/vite`)
- **Icon Library**: Lucide React (`lucide-react`)
- **Animation Library**: Motion (`motion` package)
- **Font Loading**: Google Fonts via CSS `@import`

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/index.css` | Central stylesheet containing Tailwind import, theme tokens, custom animations, and utility classes |
| `frontend/vite.config.ts` | Vite configuration with Tailwind CSS plugin integration |
| `frontend/package.json` | Dependency declarations for Tailwind, autoprefixer, and related tooling |

## Architecture and Conventions

### Typography System
Three font families are defined as CSS custom properties in the `@theme` block:
- `--font-sans`: Inter (body text, UI elements)
- `--font-display`: Space Grotesk (headings, brand text)
- `--font-mono`: JetBrains Mono (code blocks, technical content)

### Color Palette
The design uses a warm, academic color scheme centered around:
- **Primary accent**: `#7a1c1c` (deep rose/burgundy) — used for CTAs, active states, links, and user message bubbles
- **Background**: `#f8fafc` (slate-50) with fixed attachment
- **Text**: `#1e293b` (slate-800) for body, `#0f172a` (slate-900) for headings
- **Surface layers**: White with varying opacity for glass effects

### Glassmorphism Pattern
A distinctive glassmorphism aesthetic is implemented through custom utility classes in `index.css`:

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 20px 40px -15px rgba(148, 163, 184, 0.12);
}

.glass-header {
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
}
```

These classes are applied to the sidebar (`glass-panel`) and header (`glass-header`) to create layered, translucent surfaces.

### Custom Animations
Four named animations are defined in the `@theme` block using cubic-bezier easing curves:
- `fade-in`: Opacity transition (0.4s)
- `scale-up`: Scale + opacity (0.4s, with overshoot bounce)
- `slide-up`: TranslateY + opacity (0.5s)
- `bubble-in`: Combined translateY + scale + opacity (0.35s, used for chat messages)

### Component-Level Styling Patterns
Components use inline Tailwind utility classes exclusively — no CSS modules or styled-components. Common patterns include:

1. **Layout**: Fixed sidebar (`w-80`, `fixed left-0 top-0 h-screen`) with flex-based main content area (`flex-1`, `pl-80`)
2. **Spacing**: Consistent use of Tailwind spacing scale (e.g., `px-5`, `py-6`, `gap-3`)
3. **Rounded corners**: `rounded-xl` (12px), `rounded-2xl` (16px) for cards and inputs
4. **Shadows**: Custom `soft-shadow` and `soft-shadow-hover` utilities with hover lift effect (`translateY(-3px)`)
5. **Chat bubbles**: `.message-bot` (white glass) and `.message-user` (solid `#7a1c1c` background)
6. **Input fields**: `.pill-input-wrapper` with focus state that shifts shadow color to indigo/rose tones

### Scrollbar Styling
Custom WebKit scrollbar styles are applied globally:
- Width: 6px
- Thumb: `#cbd5e1` (slate-300), rounded, darkens on hover to `#94a3b8`
- Track: transparent

Inline overrides appear in scrollable containers (e.g., `[&::-webkit-scrollbar]:w-1.5`)

## Rules Developers Should Follow

1. **Use Tailwind utilities exclusively** — do not add new CSS files or use CSS-in-JS libraries. Extend `index.css` only for shared custom utilities (`.glass-panel`, `.soft-shadow`, etc.)

2. **Respect the color palette** — primary actions and active states should use `#7a1c1c` (rose-900 equivalent). Avoid introducing new accent colors without design review.

3. **Apply glassmorphism consistently** — use `.glass-panel` for side panels and `.glass-header` for sticky headers. Do not mix opaque backgrounds with glass surfaces in the same layer.

4. **Use defined typography classes** — apply `font-display` for headings, `font-sans` for body, `font-mono` for code. Font weights follow: 400 (regular), 500 (medium), 600 (semibold), 700 (bold).

5. **Leverage custom animations** — use `animate-fade-in`, `animate-scale-up`, `animate-slide-up`, or `animate-bubble-in` for element entrances. Do not create ad-hoc keyframe animations.

6. **Maintain responsive breakpoints** — the layout uses a fixed 80-unit (320px) sidebar on desktop. Ensure mobile adaptations account for this constraint.

7. **Icon consistency** — use Lucide React icons at standard sizes (14–18px for UI, 16px default). Maintain consistent stroke width.

8. **Bilingual support** — all user-facing text must go through the `i18n.ts` translation system. Do not hardcode Vietnamese or English strings in components.