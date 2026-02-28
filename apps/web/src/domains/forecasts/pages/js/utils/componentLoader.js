/**
 * Component Loader Utility
 * Charge les composants HTML de manière asynchrone
 */

/**
 * Charge un composant HTML unique
 * @param {string} path - Chemin relatif du composant (ex: 'modals/settings-modal.html')
 * @param {string} targetSelector - Sélecteur CSS de la cible (ex: '#settings-container')
 * @returns {Promise<boolean>} - true si succès, false sinon
 */
export async function loadComponent(path, targetSelector) {
    try {
        console.log(`📦 Loading component: ${path}`);

        const response = await fetch(`/components/${path}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const html = await response.text();
        const target = document.querySelector(targetSelector);

        if (!target) {
            throw new Error(`Target not found: ${targetSelector}`);
        }

        target.innerHTML = html;
        console.log(`✅ Component loaded: ${path}`);
        return true;

    } catch (error) {
        console.error(`❌ Failed to load component ${path}:`, error);
        return false;
    }
}

/**
 * Charge plusieurs composants en parallèle
 * @param {Array<{path: string, target: string}>} components - Liste des composants à charger
 * @returns {Promise<boolean[]>} - Tableau de booléens indiquant le succès de chaque chargement
 */
export async function loadComponents(components) {
    console.log(`📦 Loading ${components.length} components...`);

    const promises = components.map(({ path, target }) =>
        loadComponent(path, target)
    );

    const results = await Promise.all(promises);
    const successCount = results.filter(r => r).length;

    console.log(`✅ Loaded ${successCount}/${components.length} components`);
    return results;
}

/**
 * Charge un composant et appelle un callback quand c'est fait
 * @param {string} path - Chemin du composant
 * @param {string} targetSelector - Sélecteur de la cible
 * @param {Function} callback - Fonction à appeler après chargement
 */
export async function loadComponentWithCallback(path, targetSelector, callback) {
    const success = await loadComponent(path, targetSelector);
    if (success && callback) {
        callback();
    }
    return success;
}
