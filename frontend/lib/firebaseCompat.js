/**
 * AI-BS Drop-in Firebase-to-Supabase Compatibility Adapter
 * Translates Firestore queries & Auth methods seamlessly to Supabase PostgREST & GoTrue.
 */

import { supabase } from './supabaseClient';

export const db = { _type: 'firestore_compat' };
export const auth = {
  currentUser: { uid: 'admin_user', email: 'brett@stehouwer.com' },
  onAuthStateChanged: (cb) => {
    if (cb) cb({ uid: 'admin_user', email: 'brett@stehouwer.com' });
    return () => {};
  }
};

export const getFirestore = () => db;
export const getAuth = () => auth;

export const collection = (db, collectionName) => ({
  collectionName,
  table: `firestore_${collectionName}`
});

export const doc = (db, collectionName, docId) => ({
  collectionName,
  docId,
  table: `firestore_${collectionName}`
});

export const getDoc = async (docRef) => {
  try {
    const { data, error } = await supabase
      .from(docRef.table)
      .select('data')
      .eq('id', docRef.docId)
      .single();

    if (error || !data) {
      return {
        exists: () => false,
        data: () => null,
        id: docRef.docId
      };
    }

    return {
      exists: () => true,
      data: () => data.data,
      id: docRef.docId
    };
  } catch (err) {
    return { exists: () => false, data: () => null, id: docRef.docId };
  }
};

export const setDoc = async (docRef, data, options = {}) => {
  const { error } = await supabase
    .from(docRef.table)
    .upsert({
      id: docRef.docId,
      data: data,
      updated_at: new Date().toISOString()
    });
  if (error) throw error;
  return true;
};

export const getDocs = async (collectionRef) => {
  const { data, error } = await supabase
    .from(collectionRef.table)
    .select('id, data');

  if (error || !data) return { docs: [] };

  return {
    docs: data.map(item => ({
      id: item.id,
      data: () => item.data
    }))
  };
};

export const onSnapshot = (ref, callback) => {
  // Execute initial fetch
  if (ref.docId) {
    getDoc(ref).then(snap => callback(snap));
  } else {
    getDocs(ref).then(snap => callback(snap));
  }

  // Subscribe to realtime channel
  const channel = supabase
    .channel(`public:${ref.table}`)
    .on('postgres_changes', { event: '*', schema: 'public', table: ref.table }, payload => {
      if (ref.docId) {
        getDoc(ref).then(snap => callback(snap));
      } else {
        getDocs(ref).then(snap => callback(snap));
      }
    })
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
};
