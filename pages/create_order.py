<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Order Tracking – Shree Ram Packers</title>
<style>
body {
  font-family: Arial, sans-serif;
  background: #f6f6f6;
  padding: 20px;
}
.container {
  background: white;
  padding: 25px;
  border-radius: 10px;
  max-width: 550px;
  margin: auto;
  box-shadow: 0 3px 15px rgba(0,0,0,0.1);
}
input {
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
}
button {
  width: 100%;
  background: #0d47a1;
  color: white;
  border: none;
  padding: 12px;
  margin-top: 12px;
  border-radius: 6px;
  cursor: pointer;
}
#result {
  margin-top: 20px;
  padding: 15px;
  background: #e3f2fd;
  border-radius: 6px;
}
</style>
</head>

<body>

<div class="container">
  <h2>📦 Track Your Order</h2>
  <p>Enter Order ID or scan QR code.</p>

  <input type="text" id="orderInput" placeholder="Enter Order ID (e.g., SRP015)">
  <button onclick="trackOrder()">Track Order</button>

  <div id="result"></div>
</div>


<!-- Firebase SDK -->
<script type="module">

// ----------------------
//  FIREBASE IMPORTS
// ----------------------
import { initializeApp } 
from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";

import { 
  getDatabase, ref, get 
} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-database.js";


// ----------------------
//  CONFIG
// ----------------------
const firebaseConfig = {
  apiKey: "AIzaSyC6dSHzQ5kvfDSDcLNvRl-svNf5E2Mrmuk",
  authDomain: "omss-2ccc6.firebaseapp.com",
  databaseURL: "https://omss-2ccc6-default-rtdb.firebaseio.com",
  projectId: "omss-2ccc6",
  storageBucket: "omss-2ccc6.firebasestorage.app",
  messagingSenderId: "24897633074",
  appId: "1:24897633074:web:ddbf44965e91b17a1db52b",
  measurementId: "G-D1GBGQQJS2"
};


// ----------------------
//  INIT FIREBASE
// ----------------------
const app = initializeApp(firebaseConfig);

// IMPORTANT: Force Long Polling (Fixes "client offline")
const db = getDatabase(app, {
  experimentalForceLongPolling: true,
  experimentalAutoDetectLongPolling: true
});


// ----------------------
//  AUTO READ ORDER ID FROM URL
// ----------------------
const urlParams = new URLSearchParams(window.location.search);
const autoOrderID = urlParams.get("id");

if (autoOrderID) {
  document.getElementById("orderInput").value = autoOrderID;
  trackOrder();    // auto-run tracking
}


// ----------------------
//  TRACK ORDER FUNCTION
// ----------------------
window.trackOrder = async function () {
  const orderID = document.getElementById("orderInput").value.trim();
  const resultBox = document.getElementById("result");

  if (!orderID) {
    resultBox.innerHTML = "<p style='color:red;'>❌ Enter a valid Order ID.</p>";
    return;
  }

  resultBox.innerHTML = "⏳ Fetching order details...";

  try {
    const dbRef = ref(db, "orders");
    const snapshot = await get(dbRef);

    if (!snapshot.exists()) {
      resultBox.innerHTML = "<p style='color:red;'>❌ No orders found.</p>";
      return;
    }

    let found = null;
    snapshot.forEach(child => {
      if (child.val().order_id === orderID) {
        found = child.val();
      }
    });

    if (!found) {
      resultBox.innerHTML = "<p style='color:red;'>❌ Order not found.</p>";
      return;
    }

    resultBox.innerHTML = `
      <h3>Order Details</h3>
      <p><b>Order ID:</b> ${found.order_id}</p>
      <p><b>Customer:</b> ${found.customer}</p>
      <p><b>Product:</b> ${found.item}</p>
      <p><b>Qty:</b> ${found.qty}</p>
      <p><b>Stage:</b> ${found.stage}</p>
      <p><b>Priority:</b> ${found.priority}</p>
      <p><b>Received:</b> ${found.received}</p>
      <p><b>Due:</b> ${found.due}</p>
    `;

  } catch (err) {
    resultBox.innerHTML = `<p style="color:red;">⚠ Firebase error:<br>${err}</p>`;
    console.error("Firebase error:", err);
  }
};

</script>

</body>
</html>
