import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getMessaging, getToken } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "AIzaSyC6dSHzQ5kvfDSDcLNvRl-svNf5E2Mrmuk",
  authDomain: "omss-2ccc6.firebaseapp.com",
  projectId: "omss-2ccc6",
  messagingSenderId: "24897633074",
  appId: "1:24897633074:web:ddbf44965e91b17a1db52b"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

window.requestAdminFCM = async function () {
  try {
    const token = await getToken(messaging, {
      vapidKey: "BIk4R-HX7lZn4jxOZ5nrOvnfCSvcJk4W5pi9xCOBRVYpytMdXr1LHHBxZDozsAu6HNdD8yD8I3_wqE4QJbQAc7c"
    });

    if (token) {
      fetch("/upload_admin_token", {
        method: "POST",
        body: token
      });

      alert("Notifications enabled for admin!");
    } else {
      alert("Please allow notification permission.");
    }
  } catch (e) {
    alert("Error enabling notifications: " + e);
  }
};
