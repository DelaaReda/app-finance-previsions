/**
 * Component Loader
 * Lazy-loads HTML fragment files into DOM targets.
 */

function cloneScript(script) {
  const nextScript = document.createElement('script');
  for (const attr of script.attributes) {
    nextScript.setAttribute(attr.name, attr.value);
  }
  nextScript.textContent = script.textContent;
  return nextScript;
}

function activateInlineScripts(target) {
  const scripts = Array.from(target.querySelectorAll('script'));
  scripts.forEach((script) => {
    const nextScript = cloneScript(script);
    script.parentNode?.replaceChild(nextScript, script);
  });
}

/**
 * Load a single HTML component into a target selector.
 * @param {string} path - relative path to HTML file
 * @param {string} target - CSS selector to inject into
 */
export async function loadComponent(path, target) {
  const el = document.querySelector(target);
  if (!el) return false;
  try {
    const res = await fetch(path);
    if (res.ok) {
      el.innerHTML = await res.text();
      activateInlineScripts(el);
      return true;
    } else {
      console.warn('[ComponentLoader] 404:', path);
      return false;
    }
  } catch (e) {
    console.warn('[ComponentLoader] Error loading', path, e.message);
    return false;
  }
}

/**
 * Load multiple components in parallel.
 * @param {Array<{path: string, target: string}>} components
 */
export async function loadComponents(components) {
  return Promise.all(components.map(({ path, target }) => loadComponent(path, target)));
}

// Also expose as global for non-module scripts
window.ComponentLoader = { loadComponent, loadComponents };
