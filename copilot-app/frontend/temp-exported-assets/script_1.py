
# Créer un document CSS complet avec les styles recommandés pour l'application

css_code = """/* ============================================
   COPILOT FINANCE - IMPROVED DESIGN SYSTEM
   ============================================ */

/* ----- 1. VARIABLES CSS ----- */
:root {
  /* Couleurs principales */
  --color-primary: #288cfa;
  --color-primary-light: #7ebcf9;
  --color-primary-dark: #103766;
  
  /* Couleurs succès */
  --color-success: #2E865F;
  --color-success-light: #C6F4D6;
  --color-success-dark: #1a5238;
  
  /* Couleurs warning */
  --color-warning: #f59e0b;
  --color-warning-light: #fef3c7;
  --color-warning-dark: #d97706;
  
  /* Couleurs danger */
  --color-danger: #ef4444;
  --color-danger-light: #fee2e2;
  --color-danger-dark: #dc2626;
  
  /* Échelle de gris */
  --color-gray-50: #F5F5F5;
  --color-gray-100: #E5E7EB;
  --color-gray-300: #D1D5DB;
  --color-gray-500: #6B7280;
  --color-gray-700: #374151;
  --color-gray-900: #111827;
  
  /* Backgrounds dark mode */
  --bg-main: #0f172a;
  --bg-card: #1e293b;
  --bg-hover: #334155;
  
  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  
  /* Border radius */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 20px 25px -5px rgb(0 0 0 / 0.1);
  --shadow-glow-primary: 0 8px 32px rgba(40, 140, 250, 0.3);
  --shadow-glow-success: 0 8px 32px rgba(46, 134, 95, 0.3);
  
  /* Transitions */
  --transition-fast: all 0.15s ease;
  --transition-default: all 0.3s ease-in-out;
  --transition-slow: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ----- 2. BASE STYLES ----- */
body {
  background: var(--bg-main);
  color: var(--color-gray-100);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
}

/* ----- 3. GLASSMORPHISM CARD ----- */
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: var(--shadow-lg);
  transition: var(--transition-default);
}

.glass-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-glow-primary);
  border-color: rgba(40, 140, 250, 0.3);
}

/* ----- 4. GRADIENT CARDS ----- */
.card-gradient-primary {
  background: linear-gradient(135deg, #288cfa 0%, #7ebcf9 100%);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  position: relative;
  overflow: hidden;
  transition: var(--transition-default);
}

.card-gradient-primary:hover {
  transform: scale(1.02);
  box-shadow: var(--shadow-glow-primary);
}

.card-gradient-success {
  background: linear-gradient(135deg, #2E865F 0%, #C6F4D6 100%);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  transition: var(--transition-default);
}

/* ----- 5. GRADIENT BORDERS ----- */
.gradient-border {
  position: relative;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
}

.gradient-border::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  padding: 2px;
  background: linear-gradient(135deg, #288cfa, #7ebcf9, #2E865F);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  transition: var(--transition-default);
}

.gradient-border:hover::before {
  background: linear-gradient(135deg, #7ebcf9, #288cfa, #C6F4D6);
}

/* ----- 6. ANIMATED GRADIENT BORDER ----- */
@property --border-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}

.animated-border {
  background: 
    linear-gradient(45deg, var(--bg-card), var(--bg-card)) padding-box,
    conic-gradient(
      from var(--border-angle),
      rgba(40, 140, 250, 0.3) 80%,
      rgba(40, 140, 250, 1) 86%,
      rgba(126, 188, 249, 1) 90%,
      rgba(40, 140, 250, 1) 94%,
      rgba(40, 140, 250, 0.3)
    ) border-box;
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  animation: border-rotation 4s linear infinite;
}

@keyframes border-rotation {
  to {
    --border-angle: 360deg;
  }
}

/* ----- 7. BUTTONS ----- */
.btn-primary {
  background: linear-gradient(135deg, #288cfa 0%, #7ebcf9 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 12px 24px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-default);
  box-shadow: var(--shadow-md);
}

.btn-primary:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-glow-primary);
}

.btn-secondary {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: 12px 24px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-default);
}

.btn-secondary:hover {
  background: var(--color-primary);
  color: white;
  transform: scale(1.05);
}

/* ----- 8. CIRCULAR PROGRESS ----- */
.circular-progress {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: conic-gradient(
    var(--color-primary) calc(var(--progress) * 1%),
    var(--color-gray-700) 0
  );
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-slow);
}

.circular-progress::before {
  content: '';
  position: absolute;
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: var(--bg-card);
}

.circular-progress-value {
  position: relative;
  z-index: 1;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
}

/* ----- 9. TABLE STYLES ----- */
.table-modern {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 8px;
}

.table-modern thead th {
  background: var(--bg-card);
  padding: var(--space-md);
  text-align: left;
  font-weight: 600;
  color: var(--color-gray-300);
  text-transform: uppercase;
  font-size: 0.875rem;
  letter-spacing: 0.05em;
}

.table-modern tbody tr {
  background: rgba(255, 255, 255, 0.03);
  transition: var(--transition-fast);
}

.table-modern tbody tr:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: scale(1.01);
  box-shadow: var(--shadow-md);
}

.table-modern tbody td {
  padding: var(--space-md);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.table-modern tbody td:first-child {
  border-left: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}

.table-modern tbody td:last-child {
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}

/* ----- 10. BADGES ----- */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
  transition: var(--transition-fast);
}

.badge-success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.badge-warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.badge-danger {
  background: var(--color-danger-light);
  color: var(--color-danger-dark);
}

.badge-primary {
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
}

/* ----- 11. LOADING SKELETON ----- */
.skeleton {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.05) 25%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.05) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: var(--radius-md);
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ----- 12. HOVER GLOW EFFECT ----- */
.hover-glow {
  position: relative;
  overflow: hidden;
}

.hover-glow::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background: radial-gradient(
    circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
    rgba(40, 140, 250, 0.2) 0%,
    transparent 50%
  );
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.hover-glow:hover::after {
  opacity: 1;
}

/* ----- 13. TREND INDICATORS ----- */
.trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}

.trend-up {
  color: var(--color-success);
}

.trend-down {
  color: var(--color-danger);
}

.trend-neutral {
  color: var(--color-gray-500);
}

/* ----- 14. CARD SHADOWS GRADIENT ----- */
.card-shadow-gradient {
  position: relative;
}

.card-shadow-gradient::before {
  content: '';
  position: absolute;
  inset: -2px;
  background: linear-gradient(135deg, #288cfa, #7ebcf9);
  border-radius: var(--radius-lg);
  opacity: 0.4;
  filter: blur(20px);
  z-index: -1;
  transition: var(--transition-default);
}

.card-shadow-gradient:hover::before {
  opacity: 0.7;
  filter: blur(30px);
}

/* ----- 15. RESPONSIVE GRID ----- */
.grid-responsive {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-lg);
}

/* ----- 16. TOOLTIP ----- */
.tooltip {
  position: relative;
  display: inline-block;
}

.tooltip-text {
  visibility: hidden;
  background: var(--bg-card);
  color: var(--color-gray-100);
  text-align: center;
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  position: absolute;
  z-index: 1000;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  transition: var(--transition-fast);
  white-space: nowrap;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: var(--shadow-lg);
}

.tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}
"""

# Sauvegarder le fichier CSS
with open('copilot-finance-improved.css', 'w', encoding='utf-8') as f:
    f.write(css_code)

print("✅ Fichier CSS créé avec succès: copilot-finance-improved.css")
print(f"📝 Nombre de lignes: {len(css_code.splitlines())}")
print(f"🎨 Styles définis:")
print("   - Variables CSS (couleurs, spacing, shadows)")
print("   - Glassmorphism cards")
print("   - Gradient cards & borders")
print("   - Animated gradient borders")
print("   - Modern buttons")
print("   - Circular progress")
print("   - Modern table styles")
print("   - Badges")
print("   - Loading skeletons")
print("   - Hover effects")
print("   - Trend indicators")
print("   - Tooltips")
