const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

/**
 * Ensures media URLs are properly absolute.
 * Prepends BACKEND_URL to relative paths.
 * Returns a placeholder SVG if the path is invalid.
 */
export function getMediaUrl(urlPath, fallbackType = 'image') {
  if (!urlPath) {
    return _getFallbackPlaceholder(fallbackType);
  }
  
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://') || urlPath.startsWith('data:')) {
    return urlPath;
  }
  
  // Ensure we don't double slash if BACKEND_URL ends with / and urlPath starts with /
  const base = BACKEND_URL.endsWith('/') ? BACKEND_URL.slice(0, -1) : BACKEND_URL;
  const path = urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
  
  return `${base}${path}`;
}

function _getFallbackPlaceholder(type) {
  const text = type === 'video' ? 'Video Unavailable' : 'Image Unavailable';
  // Generates a simple SVG data URI placeholder
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <rect width="400" height="300" fill="#f0f0f0"/>
    <text x="200" y="150" font-family="sans-serif" font-size="20" fill="#999" text-anchor="middle" dominant-baseline="middle">${text}</text>
  </svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}
