import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, setPersistence, browserLocalPersistence } from "firebase/auth";
import { getPerformance } from "firebase/performance";
import { getAI, getGenerativeModel } from "firebase/ai";
import { getFirestore, initializeFirestore } from "firebase/firestore";

const firebaseConfig = {
  projectId: "ai-bs-dashboard",
  appId: "1:983916170084:web:dc6a0ca8819b81d28c8871",
  storageBucket: "ai-bs-dashboard.firebasestorage.app",
  apiKey: "AIzaSyBOI-bEW91UqWuNf1PhLnOPRZcXWRE3GDQ",
  authDomain: "ai-bs-dashboard.firebaseapp.com",
  messagingSenderId: "983916170084",
  measurementId: "G-PW7HHNVPH1"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);

// Explicitly configure long-term local persistence for Firebase Auth across browser restarts and page reloads
if (typeof window !== "undefined") {
  setPersistence(auth, browserLocalPersistence).catch((err) => {
    console.warn("Failed to configure Firebase Auth persistence:", err);
  });
}

export const googleProvider = new GoogleAuthProvider();
export let perf = null;
try {
  if (typeof window !== "undefined" && window.location.protocol === "https:" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    perf = getPerformance(app);
  }
} catch {
  perf = null;
}

// Safely initialize App Check only if supported
export let appCheck = null;
if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
  window.FIREBASE_APPCHECK_DEBUG_TOKEN = true;
}

// Initialize Firestore with resilient auto-detect long-polling fallback to bypass client-side extension / ad-blocker stream halts
let firestoreDb = null;
try {
  firestoreDb = initializeFirestore(app, {
    experimentalAutoDetectLongPolling: true,
  });
} catch {
  firestoreDb = getFirestore(app);
}
export const db = firestoreDb;

// Initialize Firebase AI Logic (Gemini Developer API)
export let ai = null;
export let model = null;
try {
  ai = getAI(app);
  model = getGenerativeModel(ai, { model: "gemini-3-pro-preview" });
} catch {
  ai = null;
  model = null;
}

export const getApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    }
  }
  return 'http://127.0.0.1:8000';
};

// Global Error Handler (Local logging instead of analytics)
if (typeof window !== "undefined") {
  window.addEventListener("error", (event) => {
    // Ignore benign net::ERR_BLOCKED_BY_CLIENT noise from client browser ad blockers
    if (event.message && event.message.includes("net::ERR_BLOCKED_BY_CLIENT")) {
      return;
    }
    console.error(`[Local Crash Handler] ${event.message} at ${event.filename}:${event.lineno}`);
  });
  window.addEventListener("unhandledrejection", (event) => {
    // Ignore benign net::ERR_BLOCKED_BY_CLIENT or network failures from browser extensions
    if (event.reason && String(event.reason).includes("ERR_BLOCKED_BY_CLIENT")) {
      return;
    }
    console.error(`[Local Crash Handler] Unhandled Promise Rejection: ${event.reason}`);
  });
}

export const syncLiveTelemetryToFirestore = async (telemetrySnapshot) => {
  if (!db || !telemetrySnapshot) return;
  try {
    const { doc, setDoc } = await import("firebase/firestore");
    await setDoc(doc(db, "ecosystem_telemetry", "live_status"), {
      ...telemetrySnapshot,
      updated_at: new Date().toISOString()
    }, { merge: true });
  } catch (e) {
    // Local offline failover - non-blocking if client ad blocker blocks firestore.googleapis.com
  }
};
