// This configuration contains only service-worker entry scripts. TypeScript's
// WebWorker library types `self` as WorkerGlobalScope; supply the service-worker
// members/events used by these entries without adding window/DOM globals.
interface WorkerGlobalScope {
  readonly clients: ServiceWorkerGlobalScope['clients'];
  skipWaiting: ServiceWorkerGlobalScope['skipWaiting'];
}

interface WorkerGlobalScopeEventMap {
  install: ExtendableEvent;
  activate: ExtendableEvent;
  fetch: FetchEvent;
}
