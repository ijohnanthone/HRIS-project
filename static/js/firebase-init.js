// HRequest HRIS - Firebase Web SDK Initialization
// Connected to Firebase Project: hr-request-7c711
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAnalytics, logEvent } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-analytics.js";
import { getDatabase, ref, set, onValue } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";

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

// Initialize Firebase App
export const app = initializeApp(firebaseConfig);
export const analytics = typeof window !== 'undefined' ? getAnalytics(app) : null;
export const database = getDatabase(app);

// Make available globally for inline scripts or console debugging
window.firebaseApp = app;
window.firebaseAnalytics = analytics;
window.firebaseDb = database;
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

console.log("⚡ HRequest connected to Firebase Project: hr-request-7c711");
