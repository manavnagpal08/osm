importScripts("https://www.gstatic.com/firebasejs/9.22.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyC6dSHzQ5kvfDSDcLNvRl-svNf5E2Mrmuk",
  authDomain: "omss-2ccc6.firebaseapp.com",
  projectId: "omss-2ccc6",
  messagingSenderId: "24897633074",
  appId: "1:24897633074:web:ddbf44965e91b17a1db52b"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  self.registration.showNotification(payload.notification.title, {
    body: payload.notification.body
  });
});
