let currentApiBase = 'http://127.0.0.1:8000';

export const getApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return currentApiBase || 'http://127.0.0.1:8000';
    }
    if (window.location.protocol === 'https:') {
      return (currentApiBase && currentApiBase.startsWith('https:')) ? currentApiBase : 'https://api.brettstehouwer.live';
    }
    if (/^\d+\.\d+\.\d+\.\d+$/.test(window.location.hostname)) {
      return `http://${window.location.hostname}:8000`;
    }
  }
  return currentApiBase || 'http://127.0.0.1:8000';
};

export const setApiBase = (url) => {
  if (url) {
    currentApiBase = url;
  }
};

export default { getApiBase, setApiBase };
