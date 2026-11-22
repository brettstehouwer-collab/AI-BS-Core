import { auth } from '../firebase.js';

export async function chatAuthHeaders(headers = {}, expectedUid = '', { forceRefresh = false } = {}) {
  const user = auth.currentUser;
  if (!user || (expectedUid && user.uid !== expectedUid)) {
    throw new Error('Sign in to use BS-Chat.');
  }
  const token = await user.getIdToken(forceRefresh);
  if (auth.currentUser?.uid !== user.uid) throw new Error('The signed-in account changed. Try again from the current account.');
  return { ...headers, Authorization: `Bearer ${token}` };
}
