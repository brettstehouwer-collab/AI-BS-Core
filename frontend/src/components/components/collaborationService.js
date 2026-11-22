/** @typedef {{email?:string|null,displayName?:string|null}} CollaborationUser */
/** @typedef {{tab:string,url:string,name:string,icon:string}} TeamToolLink */
/** @typedef {{id:string,email:string,aliases:string[],name:string,role:string,avatar:string,color:string,status:string,currentTab:string,activeDevices?:{device:string,tab:string,email:string}[],deviceBadge?:string|null}} TeamPresence */
/** @typedef {{id:string,channelId?:string,senderEmail?:string,senderName?:string,senderAvatar?:string,senderRole?:string,senderDevice?:string,text?:string,toolLink?:TeamToolLink|null,reactions?:Record<string,string[]>,timestamp?:number}} TeamMessage */
/** @typedef {{id:string,_id?:string,userEmail?:string,userName?:string,userAvatar?:string,userRole?:string,action?:string,toolName?:string,tabKey?:string,details?:string,timestamp?:number}} TeamActivity */
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

/** @param {string|null} email */
export const getFriendlyUserName = (email = '') => {
  const lower = (email || '').toLowerCase().trim();
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

/** @param {string|null} email */
export const getFriendlyUserRole = (email = '') => {
  const lower = (email || '').toLowerCase().trim();
  if (lower.includes('julie')) return 'Executive Partner';
  if (lower.includes('theseandaley') || lower.includes('sean@stehouwer')) return 'Production & Creative Partner';
  if (lower.includes('brett') || lower.includes('footballstar') || lower.includes('footballsyat')) return 'Founder & CTO';
  if (lower.includes('rottierannajoy')) return 'Executive Partner & Strategy';
  if (lower.includes('evolution6media') || lower.includes('keith@')) return 'Media & Production Partner';
  if (lower.includes('devin') || lower.includes('feexpress')) return 'Logistics Dispatcher';
  return 'Stehouwer Publishing Admin';
};

/** @param {string|null} email */
export const getFriendlyUserAvatar = (email = '') => {
  const lower = (email || '').toLowerCase().trim();
  if (lower.includes('julie')) return '🌸';
  if (lower.includes('theseandaley') || lower.includes('sean@stehouwer')) return '🎬';
  if (lower.includes('brett') || lower.includes('footballstar') || lower.includes('footballsyat')) return '👑';
  if (lower.includes('rottierannajoy')) return '✨';
  if (lower.includes('evolution6media') || lower.includes('keith@')) return '🎥';
  if (lower.includes('devin') || lower.includes('feexpress')) return '🚚';
  return '👤';
};

/** @type {ReturnType<typeof setInterval>|null} */
let presenceInterval = null;

/** @param {CollaborationUser|null|undefined} currentUser */
export const startPresenceHeartbeat = (currentUser, activeTab = 'dashboard') => {
  if (!currentUser?.email || !db) return;
  // Guard against unauthenticated Firestore channel write attempts in dev
  if (auth && !auth.currentUser) return;

  const presenceEmail = currentUser.email;
  const emailKey = presenceEmail.toLowerCase().replace(/[^a-zA-Z0-9_]/g, '_');
  const presenceRef = doc(db, 'admin_presence', emailKey);

  const sendHeartbeat = async () => {
    try {
      await setDoc(presenceRef, {
        email: presenceEmail.toLowerCase(),
        displayName: currentUser.displayName || getFriendlyUserName(currentUser.email),
        avatar: getFriendlyUserAvatar(currentUser.email),
        role: getFriendlyUserRole(currentUser.email),
        currentTab: activeTab,
        lastSeen: Date.now(),
        isOnline: true,
        updatedAt: serverTimestamp()
      }, { merge: true });
    } catch (err) {
      console.warn('[Presence] Heartbeat failed:', errorMessage(err));
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

/** @param {(members:TeamPresence[])=>void} callback */
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
    /** @type {Record<string,{email:string,lastSeen:number,currentTab:string,status:string,secondsAgo:number}>} */
    const presenceMap = {};

    snapshot.forEach(docSnap => {
      const data = /** @type {{email:string,lastSeen:number,currentTab:string,isOnline:boolean}} */ (docSnap.data());
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

/** @param {{channelId?:string,senderEmail?:string|null,senderName?:string|null,text:string,toolLink?:TeamToolLink|null,senderDevice?:string}} options */
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

/** @param {string} messageId @param {string} emoji @param {string|null|undefined} userEmail */
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
      updatedList = userList.filter(/** @param {unknown} e */ e => e !== email);
    } else {
      updatedList = [...userList, email];
    }
    const updatedReactions = { ...currentReactions, [emoji]: updatedList };
    if (updatedList.length === 0) {
      delete updatedReactions[emoji];
    }
    await updateDoc(msgRef, { reactions: updatedReactions });
  } catch (err) {
    console.warn('[Chat] Failed to toggle reaction:', errorMessage(err));
  }
};

/** @param {string} channelId @param {(messages:TeamMessage[])=>void} callback */
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
    /** @type {TeamMessage[]} */
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

/** @param {{user?:CollaborationUser|null,action:string,toolName?:string,tabKey?:string,details?:string}} options */
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
    console.warn('[Activity] Failed to log activity:', errorMessage(err));
  }
};

/** @param {(activities:TeamActivity[])=>void} callback */
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
    /** @type {TeamActivity[]} */
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

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
