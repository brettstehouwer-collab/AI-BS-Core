let currentApiBase = 'http://127.0.0.1:8000';

export const getApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return currentApiBase || 'http://127.0.0.1:8000';
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
