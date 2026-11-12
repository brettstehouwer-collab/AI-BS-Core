import React from '/src/utils/applicationReact.js';

// Use the application's React copy; nested component dependencies contain another version.
// Execution stays unavailable until the independent disposable worker is accepted.
export default function VirtualMachineTab() {
  const element = React.createElement;
  return element('section', { 'aria-labelledby': 'vm-verification-title', style: { padding: '24px', color: '#e2e8f0', maxWidth: '760px' } },
    element('h2', { id: 'vm-verification-title' }, 'Virtual machines'),
    element('p', { role: 'status' }, element('strong', null, 'Verification unavailable')),
    element('p', null, 'The separate disposable worker is being prepared. Its diagnostic checks must pass before verification becomes available here.'),
    element('button', { type: 'button', disabled: true }, 'Verify in disposable VM'),
    element('p', null, 'No verification job has been run from this page.')
  );
}
