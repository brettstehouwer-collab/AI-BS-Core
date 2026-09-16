import { db, auth } from '../firebase';
import { 
  collection, 
  doc, 
  setDoc, 
  addDoc, 
  query, 
  where, 
  orderBy, 
  limit, 
  onSnapshot, 
  serverTimestamp 
} from 'firebase/firestore';

export const KNOWN_TEAM_MEMBERS = [
  {
    email: 'brettstehouwer@gmail.com',
    name: 'Brett Stehouwer',
    role: 'Founder & CTO',
    avatar: '👑',
    color: '#38bdf8'
  },
  {
    email: 'stehouwerjulie@gmail.com',
    name: 'Julie Stehouwer (Mom)',
    role: 'Executive Partner',
    avatar: '🌸',
    color: '#ec4899'
  },
  {
    email: 'theseandaley@gmail.com',
    name: 'Sean Daley',
    role: 'Production & Creative Partner',
    avatar: '🎬',
    color: '#a855f7'
  },
  {
    email: 'footballstar0325@gmail.com',
    name: 'Brett Stehouwer (Mobile)',
    role: 'Lead Administrator',
    avatar: '⚡',
    color: '#38bdf8'
  }
];

export const getFriendlyUserName = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return 'Julie Stehouwer (Mom)';
  if (lower.includes('theseandaley')) return 'Sean Daley';
  if (lower.includes('brett') || lower.includes('footballstar')) return 'Brett Stehouwer';
  const found = KNOWN_TEAM_MEMBERS.find(m => m.email.toLowerCase() === lower);
  if (found) return found.name;
  if (!email) return 'Admin User';
  return email.split('@')[0];
};

export const getFriendlyUserRole = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return 'Executive Partner';
  if (lower.includes('theseandaley')) return 'Production Partner';
  if (lower.includes('brett') || lower.includes('footballstar')) return 'Founder & CTO';
  return 'Stehouwer Publishing Admin';
};

export const getFriendlyUserAvatar = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return '🌸';
  if (lower.includes('theseandaley')) return '🎬';
  if (lower.includes('brett') || lower.includes('footballstar')) return '👑';
  return '👤';
};

let presenceInterval = null;

export const startPresenceHeartbeat = (currentUser, activeTab = 'dashboard') => {
  if (!currentUser?.email || !db) return;
  // Guard against unauthenticated Firestore channel write attempts in dev
  if (auth && !auth.currentUser) return;

  const emailKey = currentUser.email.toLowerCase().replace(/[^a-zA-Z0-9_]/g, '_');
  const presenceRef = doc(db, 'admin_presence', emailKey);

  const sendHeartbeat = async () => {
    try {
      await setDoc(presenceRef, {
        email: currentUser.email.toLowerCase(),
        displayName: currentUser.displayName || getFriendlyUserName(currentUser.email),
        avatar: getFriendlyUserAvatar(currentUser.email),
        role: getFriendlyUserRole(currentUser.email),
        currentTab: activeTab,
        lastSeen: Date.now(),
        isOnline: true,
        updatedAt: serverTimestamp()
      }, { merge: true });
    } catch (err) {
      console.warn('[Presence] Heartbeat failed:', err.message);
    }
  };

  sendHeartbeat();

  if (presenceInterval) clearInterval(presenceInterval);
  presenceInterval = setInterval(sendHeartbeat, 25000);

  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
      try {
        setDoc(presenceRef, { isOnline: false, lastSeen: Date.now() }, { merge: true });
      } catch {}
    });
  }
};

export const stopPresenceHeartbeat = () => {
  if (presenceInterval) {
    clearInterval(presenceInterval);
    presenceInterval = null;
  }
};

export const subscribeToPresence = (callback) => {
  if (!db) return () => {};

  // If Firebase auth is not signed in (e.g. local offline dev), avoid initiating failing Firestore watch channels
  if (auth && !auth.currentUser) {
    callback(KNOWN_TEAM_MEMBERS.map(member => ({
      ...member,
      status: 'offline',
      currentTab: 'Offline'
    })));
    return () => {};
  }

  const presenceCol = collection(db, 'admin_presence');
  return onSnapshot(presenceCol, (snapshot) => {
    const now = Date.now();
    const presenceMap = {};

    snapshot.forEach(docSnap => {
      const data = docSnap.data();
      const lastSeenTime = data.lastSeen || 0;
      const secondsAgo = (now - lastSeenTime) / 1000;

      const isActuallyOnline = data.isOnline && secondsAgo < 65;
      const isAway = !isActuallyOnline && secondsAgo < 600;

      presenceMap[data.email] = {
        ...data,
        status: isActuallyOnline ? 'online' : (isAway ? 'away' : 'offline'),
        secondsAgo: Math.round(secondsAgo)
      };
    });

    const combined = KNOWN_TEAM_MEMBERS.map(member => {
      const liveData = presenceMap[member.email.toLowerCase()];
      return {
        ...member,
        ...(liveData || {}),
        status: liveData?.status || 'offline',
        currentTab: liveData?.currentTab || 'Offline'
      };
    });

    callback(combined);
  }, (err) => {
    if (err.code === 'permission-denied' || err.code === 'unauthenticated') {
      callback(KNOWN_TEAM_MEMBERS.map(member => ({
        ...member,
        status: 'offline',
        currentTab: 'Offline'
      })));
      return;
    }
    console.warn('[Presence] Snapshot error:', err.message);
  });
};

export const sendTeamMessage = async ({
  channelId = 'general_team',
  senderEmail,
  senderName,
  text,
  toolLink = null
}) => {
  if (!db || !text?.trim()) return;

  try {
    const messagesCol = collection(db, 'team_messages');
    await addDoc(messagesCol, {
      channelId,
      senderEmail: senderEmail?.toLowerCase() || 'admin@stehouwer.live',
      senderName: senderName || getFriendlyUserName(senderEmail),
      senderAvatar: getFriendlyUserAvatar(senderEmail),
      text: text.trim(),
      toolLink: toolLink || null,
      timestamp: Date.now(),
      createdAt: serverTimestamp()
    });
  } catch (err) {
    console.error('[Chat] Failed to send message:', err);
    throw err;
  }
};

export const subscribeToChannelMessages = (channelId, callback) => {
  if (!db) return () => {};

  // If Firebase auth is not signed in, avoid initiating failing Firestore watch channels
  if (auth && !auth.currentUser) {
    callback([]);
    return () => {};
  }

  const messagesCol = collection(db, 'team_messages');
  const q = query(
    messagesCol,
    where('channelId', '==', channelId),
    limit(100)
  );

  return onSnapshot(q, (snapshot) => {
    const msgs = [];
    snapshot.forEach(docSnap => {
      msgs.push({ id: docSnap.id, ...docSnap.data() });
    });
    // In-memory sorting to avoid Firestore composite index requirement
    msgs.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
    callback(msgs);
  }, (err) => {
    if (err.code === 'permission-denied' || err.code === 'unauthenticated') {
      callback([]);
      return;
    }
    console.warn('[Chat] Snapshot error:', err.message);
  });
};

export const logTeamActivity = async ({
  user,
  action,
  toolName = 'General Workspace',
  tabKey = 'dashboard',
  details = ''
}) => {
  if (!db || !action) return;

  const email = (user?.email || 'admin@stehouwer.live').toLowerCase();
  const userName = user?.displayName || getFriendlyUserName(email);

  try {
    const activityCol = collection(db, 'team_activity');
    await addDoc(activityCol, {
      userEmail: email,
      userName,
      userAvatar: getFriendlyUserAvatar(email),
      userRole: getFriendlyUserRole(email),
      action,
      toolName,
      tabKey,
      details: details ? details.slice(0, 300) : '',
      timestamp: Date.now(),
      createdAt: serverTimestamp()
    });
  } catch (err) {
    console.warn('[Activity] Failed to log activity:', err.message);
  }
};

export const subscribeToTeamActivity = (callback, maxItems = 20) => {
  if (!db) return () => {};

  if (auth && !auth.currentUser) {
    callback([]);
    return () => {};
  }

  const activityCol = collection(db, 'team_activity');
  const q = query(
    activityCol,
    orderBy('timestamp', 'desc'),
    limit(maxItems)
  );

  return onSnapshot(q, (snapshot) => {
    const activities = [];
    snapshot.forEach(docSnap => {
      activities.push({ id: docSnap.id, ...docSnap.data() });
    });
    callback(activities);
  }, (err) => {
    if (err.code === 'permission-denied' || err.code === 'unauthenticated') {
      callback([]);
      return;
    }
    console.warn('[Activity] Snapshot error:', err.message);
  });
};
