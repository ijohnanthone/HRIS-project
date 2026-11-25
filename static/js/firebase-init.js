// HRequest HRIS - Firebase Web SDK Initialization
// Connected to Firebase Project: hr-request-7c711 (Region: asia-southeast1)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAnalytics, isSupported, logEvent } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-analytics.js";
import { getDatabase, ref, set, onValue, push, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";

export const firebaseConfig = {
  apiKey: "AIzaSyAFJYOX9z6GyNnkAhLoQrbwvMZbmFHELhk",
  authDomain: "hr-request-7c711.firebaseapp.com",
  databaseURL: "https://hr-request-7c711-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "hr-request-7c711",
  storageBucket: "hr-request-7c711.firebasestorage.app",
  messagingSenderId: "436829584638",
  appId: "1:436829584638:web:5ae78a2f0bf559996839af",
  measurementId: "G-85SLF46BVR"
};

// 1. Initialize Firebase App
export const app = initializeApp(firebaseConfig);

// 2. Initialize Realtime Database (Guaranteed even if Analytics is blocked by ad-blockers)
export const database = getDatabase(app);

// 3. Initialize Analytics safely (with isSupported check)
export let analytics = null;
try {
  const analyticsSupported = await isSupported();
  if (analyticsSupported) {
    analytics = getAnalytics(app);
  }
} catch (err) {
  console.info("[Firebase Analytics] Analytics skipped or blocked:", err.message);
}

// 4. Global window exports for seamless client-side usage in templates
window.firebaseApp = app;
window.firebaseDb = database;
window.firebaseAnalytics = analytics;
window.firebaseRef = ref;
window.firebaseSet = set;
window.firebasePush = push;
window.firebaseOnValue = onValue;
window.firebaseServerTimestamp = serverTimestamp;

// Helper function to broadcast real-time HR events (e.g. punch notifications, ticket alerts)
window.publishRealtimeNotice = (category, payload) => {
  if (database) {
    try {
      const noticesRef = ref(database, `live_notices/${category}`);
      return push(noticesRef, {
        ...payload,
        timestamp: Date.now()
      });
    } catch (e) {
      console.warn("[Firebase RTDB] Publish failed:", e);
    }
  }
};

// Helper function to log telemetry events
window.logFirebaseEvent = (eventName, params = {}) => {
  if (analytics) {
    try {
      logEvent(analytics, eventName, params);
      console.log(`[Firebase Analytics] Event logged: ${eventName}`, params);
    } catch (e) {
      console.warn("[Firebase Analytics] Event failed:", e);
    }
  }
};

console.log("⚡ HRequest connected to Firebase Project: hr-request-7c711 (RTDB & Analytics Ready)");
