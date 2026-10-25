// Fetch uses the application's admin-token interceptor; native EventSource cannot add that header.
export function createAuthenticatedEventSource(url) {
  const controller = new AbortController();
  let closed = false;
  const source = {
    onmessage: null, onerror: null,
    close() { closed = true; controller.abort(); },
  };
  Promise.resolve().then(async () => {
    let reader;
    try {
      const response = await fetch(url, {
        headers: { Accept: 'text/event-stream' }, signal: controller.signal,
      });
      if (!response.ok) throw Object.assign(new Error(`Progress stream returned HTTP ${response.status}`), { status: response.status });
      if (!response.body) throw new Error('Progress stream has no response body.');
      reader = response.body.getReader();
      const decoder = new TextDecoder();
      let pending = '';
      while (!closed) {
        const { value, done } = await reader.read();
        pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
        let separator;
        while (!closed && (separator = /\r?\n\r?\n/.exec(pending))) {
          const block = pending.slice(0, separator.index);
          pending = pending.slice(separator.index + separator[0].length);
          const data = block.split(/\r?\n/).filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).replace(/^ /, '')).join('\n');
          if (data) source.onmessage?.({ data });
        }
        if (done) break;
      }
    } catch (error) {
      if (!closed && error.name !== 'AbortError') source.onerror?.(error);
    } finally {
      if (reader) await reader.cancel().catch(() => {});
    }
  });
  return source;
}
