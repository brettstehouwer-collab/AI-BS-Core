import { db, auth } from '../firebase';
import { 
  collection, 
  doc, 
  setDoc, 
  getDoc,
  updateDoc,
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
    id: 'brett',
    email: 'brett@stehouwerproductions.com',
    aliases: [
      'brett@stehouwerproductions.com',
      'brett@stehouwerpublishing.com',
      'brettstehouwer@gmail.com',
      'footballstar0325@gmail.com',
      'footballsyat0325@gmail.com'
    ],
    name: 'Brett Stehouwer',
    role: 'Founder & CTO',
    avatar: '👑',
    color: '#38bdf8'
  },
  {
    id: 'julie',
    email: 'stehouwerjulie@gmail.com',
    aliases: [
      'stehouwerjulie@gmail.com',
      'julie.a.stehouwer@gmail.com',
      'julieannstehouwer@gmail.com',
      'juliestehouwer@gmail.com',
      'stehouwer.julie@gmail.com',
      'julie@stehouwerpublishing.com',
      'stehouwer@gmail.com'
    ],
    name: 'Julie Stehouwer (Mom)',
    role: 'Executive Partner',
    avatar: '🌸',
    color: '#ec4899'
  },
  {
    id: 'sean',
    email: 'theseandaley@gmail.com',
    aliases: [
      'theseandaley@gmail.com',
      'sean@stehouwerpublishing.com'
    ],
    name: 'Sean Daley',
    role: 'Production & Creative Partner',
    avatar: '🎬',
    color: '#a855f7'
  },
  {
    id: 'anna',
    email: 'rottierannajoy@gmail.com',
    aliases: [
      'rottierannajoy@gmail.com'
    ],
    name: 'Anna Joy Rottier',
    role: 'Executive Partner & Strategy',
    avatar: '✨',
    color: '#10b981'
  },
  {
    id: 'keith',
    email: 'keith@evolution6media.com',
    aliases: [
      'keith@evolution6media.com'
    ],
    name: 'Keith (Evolution 6 Media)',
    role: 'Media & Production Partner',
    avatar: '🎥',
    color: '#f59e0b'
  },
  {
    id: 'devin',
    email: 'devin@feexpress.com',
    aliases: [
      'devin@feexpress.com',
      'devin.feexpress@gmail.com'
    ],
    name: 'Devin (FE Express Logistics)',
    role: 'Logistics Dispatcher',
    avatar: '🚚',
    color: '#06b6d4'
  }
];

export const getFriendlyUserName = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return 'Julie Stehouwer (Mom)';
  if (lower.includes('theseandaley') || lower.includes('sean@stehouwer')) return 'Sean Daley';
  if (lower.includes('brett') || lower.includes('footballstar') || lower.includes('footballsyat')) return 'Brett Stehouwer';
  if (lower.includes('rottierannajoy')) return 'Anna Joy Rottier';
  if (lower.includes('evolution6media') || lower.includes('keith@')) return 'Keith (Evolution 6 Media)';
  if (lower.includes('devin') || lower.includes('feexpress')) return 'Devin (FE Express)';
  const found = KNOWN_TEAM_MEMBERS.find(m => m.aliases && m.aliases.some(a => a.toLowerCase() === lower));
  if (found) return found.name;
  if (!email) return 'Admin User';
  return email.split('@')[0];
};

export const getFriendlyUserRole = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return 'Executive Partner';
  if (lower.includes('theseandaley') || lower.includes('sean@stehouwer')) return 'Production & Creative Partner';
  if (lower.includes('brett') || lower.includes('footballstar') || lower.includes('footballsyat')) return 'Founder & CTO';
  if (lower.includes('rottierannajoy')) return 'Executive Partner & Strategy';
  if (lower.includes('evolution6media') || lower.includes('keith@')) return 'Media & Production Partner';
  if (lower.includes('devin') || lower.includes('feexpress')) return 'Logistics Dispatcher';
  return 'Stehouwer Publishing Admin';
};

export const getFriendlyUserAvatar = (email = '') => {
  const lower = email.toLowerCase().trim();
  if (lower.includes('julie')) return '🌸';
  if (lower.includes('theseandaley') || lower.includes('sean@stehouwer')) return '🎬';
  if (lower.includes('brett') || lower.includes('footballstar') || lower.includes('footballsyat')) return '👑';
  if (lower.includes('rottierannajoy')) return '✨';
  if (lower.includes('evolution6media') || lower.includes('keith@')) return '🎥';
  if (lower.includes('devin') || lower.includes('feexpress')) return '🚚';
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
      const activeDevices = [];
      let overallStatus = 'offline';
      let latestTab = 'Offline';
      let latestSeen = 0;

      for (const alias of (member.aliases || [member.email])) {
        const live = presenceMap[alias.toLowerCase()];
        if (live) {
          if (live.status === 'online') {
            overallStatus = 'online';
            const deviceName = alias.includes('footballstar') ? 'Mobile' : (alias.includes('gmail') ? 'Studio PC' : 'Production Web');
            activeDevices.push({
              device: deviceName,
              tab: live.currentTab || 'Active',
              email: alias
            });
            if (live.lastSeen > latestSeen) {
              latestSeen = live.lastSeen;
              latestTab = live.currentTab;
            }
          } else if (live.status === 'away' && overallStatus !== 'online') {
            overallStatus = 'away';
          }
        }
      }

      return {
        ...member,
        status: overallStatus,
        currentTab: latestTab,
        activeDevices: activeDevices,
        deviceBadge: activeDevices.length > 0 
          ? activeDevices.map(d => `${d.device === 'Mobile' ? '📱' : '🖥️'} ${d.device} (${d.tab})`).join(' · ')
          : null
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
  toolLink = null,
  senderDevice = 'Desktop'
}) => {
  if (!db || !text?.trim()) return;

  try {
    const messagesCol = collection(db, 'team_messages');
    await addDoc(messagesCol, {
      channelId,
      senderEmail: senderEmail?.toLowerCase() || 'admin@stehouwer.live',
      senderName: senderName || getFriendlyUserName(senderEmail),
      senderAvatar: getFriendlyUserAvatar(senderEmail),
      senderRole: getFriendlyUserRole(senderEmail),
      senderDevice: senderDevice || 'Desktop',
      text: text.trim(),
      toolLink: toolLink || null,
      reactions: {},
      timestamp: Date.now(),
      createdAt: serverTimestamp()
    });
  } catch (err) {
    console.error('[Chat] Failed to send message:', err);
    throw err;
  }
};

export const toggleMessageReaction = async (messageId, emoji, userEmail) => {
  if (!db || !messageId || !emoji || !userEmail) return;
  try {
    const msgRef = doc(db, 'team_messages', messageId);
    const msgSnap = await getDoc(msgRef);
    if (!msgSnap.exists()) return;
    const currentReactions = msgSnap.data().reactions || {};
    const email = userEmail.toLowerCase();
    const userList = currentReactions[emoji] || [];
    let updatedList;
    if (userList.includes(email)) {
      updatedList = userList.filter(e => e !== email);
    } else {
      updatedList = [...userList, email];
    }
    const updatedReactions = { ...currentReactions, [emoji]: updatedList };
    if (updatedList.length === 0) {
      delete updatedReactions[emoji];
    }
    await updateDoc(msgRef, { reactions: updatedReactions });
  } catch (err) {
    console.warn('[Chat] Failed to toggle reaction:', err.message);
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
