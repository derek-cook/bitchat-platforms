const BITCHAT_SERVICE_UUID = "f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c";
const BITCHAT_CHAR_UUID = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d";

let currentDevice = null;
let currentServer = null;
let currentCharacteristic = null;
let discoveredDevices = [];
let isListening = false;

const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const scanBtn = document.getElementById("scanBtn");
const sendBtn = document.getElementById("sendBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const listenBtn = document.getElementById("listenBtn");

function log(message, type = "info") {
  const entry = document.createElement("div");
  entry.className = `log-entry ${type}`;
  entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
  logEl.insertBefore(entry, logEl.firstChild);

  if (logEl.children.length > 50) {
    logEl.removeChild(logEl.lastChild);
  }
}

function setStatus(text, className) {
  statusEl.textContent = text;
  statusEl.className = `status ${className}`;
}

function generateSenderId() {
  const id = new Uint8Array(8);
  crypto.getRandomValues(id);
  return id;
}

function generateAnnouncePacket(senderId, senderName, ttl = 3) {
  const encoder = new TextEncoder();
  const nameBytes = encoder.encode(senderName);
  const timestamp = Date.now();

  const packet = new ArrayBuffer(15 + 8 + nameBytes.length);
  const view = new DataView(packet);
  const uint8View = new Uint8Array(packet);

  let offset = 0;

  view.setUint8(offset++, 0x01);
  view.setUint8(offset++, 0x01);

  view.setUint8(offset++, ttl);

  view.setBigUint64(offset, BigInt(timestamp), false);
  offset += 8;

  view.setUint8(offset++, 0x00);

  view.setUint16(offset, nameBytes.length, false);
  offset += 2;

  uint8View.set(senderId, offset);
  offset += senderId.length;

  uint8View.set(nameBytes, offset);

  return new Uint8Array(packet);
}

function generateMessagePacket(senderId, senderName, content, ttl = 3) {
  const encoder = new TextEncoder();
  const nameBytes = encoder.encode(senderName);
  const contentBytes = encoder.encode(content);
  const timestamp = Date.now();

  const uid = crypto.randomUUID();
  const uidBytes = encoder.encode(uid);

  const messageLength =
    1 +
    8 +
    1 +
    uidBytes.length +
    1 +
    nameBytes.length +
    2 +
    contentBytes.length +
    1 +
    senderId.length;

  const message = new ArrayBuffer(messageLength);
  const msgView = new DataView(message);
  const msgUint8View = new Uint8Array(message);

  let msgOffset = 0;

  msgView.setUint8(msgOffset++, 0x10);

  msgView.setBigUint64(msgOffset, BigInt(timestamp), false);
  msgOffset += 8;

  msgView.setUint8(msgOffset++, uidBytes.length);
  msgUint8View.set(uidBytes, msgOffset);
  msgOffset += uidBytes.length;

  msgView.setUint8(msgOffset++, nameBytes.length);
  msgUint8View.set(nameBytes, msgOffset);
  msgOffset += nameBytes.length;

  msgView.setUint16(msgOffset, contentBytes.length, false);
  msgOffset += 2;
  msgUint8View.set(contentBytes, msgOffset);
  msgOffset += contentBytes.length;

  msgView.setUint8(msgOffset++, senderId.length);
  msgUint8View.set(senderId, msgOffset);

  const packetLength = 15 + 8 + 8 + messageLength;
  const packet = new ArrayBuffer(packetLength);
  const view = new DataView(packet);
  const uint8View = new Uint8Array(packet);

  let offset = 0;

  view.setUint8(offset++, 0x01);
  view.setUint8(offset++, 0x04);

  view.setUint8(offset++, ttl);

  view.setBigUint64(offset, BigInt(timestamp), false);
  offset += 8;

  view.setUint8(offset++, 0x01);

  view.setUint16(offset, messageLength, false);
  offset += 2;

  uint8View.set(senderId, offset);
  offset += senderId.length;

  uint8View.set(
    new Uint8Array([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
    offset
  );
  offset += 8;

  uint8View.set(new Uint8Array(message), offset);

  return new Uint8Array(packet);
}

async function scanForDevices() {
  try {
    if (!navigator.bluetooth) {
      throw new Error("Web Bluetooth API is not available in this browser");
    }

    setStatus("Scanning...", "scanning");
    log("Starting Bluetooth scan...");
    scanBtn.disabled = true;

    const device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [BITCHAT_SERVICE_UUID] }],
      optionalServices: [BITCHAT_SERVICE_UUID],
    });

    log(`Found device: ${device.name || "Unknown"}`, "success");

    setStatus("Connecting...", "scanning");
    const server = await device.gatt.connect();

    log("Connected to GATT server", "success");

    const service = await server.getPrimaryService(BITCHAT_SERVICE_UUID);
    const characteristic = await service.getCharacteristic(BITCHAT_CHAR_UUID);

    currentDevice = device;
    currentServer = server;
    currentCharacteristic = characteristic;

    setStatus(`Connected to ${device.name || "Device"}`, "connected");
    log("Ready to send messages", "success");

    sendBtn.disabled = false;
    disconnectBtn.disabled = false;
    listenBtn.disabled = false;
    scanBtn.disabled = true;

    device.addEventListener("gattserverdisconnected", onDisconnected);
  } catch (error) {
    log(`Error: ${error.message}`, "error");
    setStatus("Disconnected", "disconnected");
    scanBtn.disabled = false;
  }
}
document.getElementById("scanBtn").addEventListener("click", scanForDevices);

function onDisconnected() {
  log("Device disconnected", "error");
  setStatus("Disconnected", "disconnected");
  currentDevice = null;
  currentServer = null;
  currentCharacteristic = null;
  isListening = false;
  scanBtn.disabled = false;
  sendBtn.disabled = true;
  disconnectBtn.disabled = true;
  listenBtn.disabled = true;
  listenBtn.textContent = "Start Listening";
}

async function sendMessages() {
  if (!currentCharacteristic) {
    log("Not connected to any device", "error");
    return;
  }

  const senderName = document.getElementById("senderName").value.trim();
  const message = document.getElementById("message").value.trim();
  const numMessages = parseInt(
    document.getElementById("numMessages")?.value || 1
  );

  if (!senderName || !message) {
    log("Please enter both sender name and message", "error");
    return;
  }

  try {
    sendBtn.disabled = true;
    const senderId = generateSenderId();

    log("Sending announce packet...");
    const announcePacket = generateAnnouncePacket(senderId, senderName);
    await currentCharacteristic.writeValueWithoutResponse(announcePacket);
    await new Promise((resolve) => setTimeout(resolve, 500));

    for (let i = 0; i < numMessages; i++) {
      log(`Sending message ${i + 1}/${numMessages}...`);
      const messagePacket = generateMessagePacket(
        senderId,
        senderName,
        message,
        5
      );
      await currentCharacteristic.writeValueWithoutResponse(messagePacket);
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    log(`Successfully sent ${numMessages} message(s)`, "success");
  } catch (error) {
    log(`Failed to send: ${error.message}`, "error");
  } finally {
    sendBtn.disabled = false;
  }
}
document.getElementById("sendBtn").addEventListener("click", sendMessages);

async function disconnect() {
  if (currentServer) {
    try {
      await currentServer.disconnect();
      log("Disconnected from device", "success");
    } catch (error) {
      log(`Error disconnecting: ${error.message}`, "error");
    }
  }
  onDisconnected();
}
document.getElementById("disconnectBtn").addEventListener("click", disconnect);

async function broadcastToAll() {
  try {
    if (!navigator.bluetooth) {
      throw new Error("Web Bluetooth API is not available in this browser");
    }

    const senderName = document.getElementById("senderName").value.trim();
    const message = document.getElementById("message").value.trim();
    const numMessages = parseInt(
      document.getElementById("numMessages")?.value || 1
    );

    if (!senderName || !message) {
      log("Please enter both sender name and message", "error");
      return;
    }

    setStatus("Broadcasting...", "scanning");
    log("Starting broadcast to all nearby BitChat devices...");
    document.getElementById("broadcastBtn").disabled = true;

    const senderId = generateSenderId();
    let devicesFound = 0;
    let messagesSent = 0;

    log(
      "Note: Browser will show device picker for each device. Select all BitChat devices."
    );

    let continueBroadcast = true;
    while (continueBroadcast) {
      try {
        const device = await navigator.bluetooth.requestDevice({
          filters: [{ services: [BITCHAT_SERVICE_UUID] }],
          optionalServices: [BITCHAT_SERVICE_UUID],
        });

        if (discoveredDevices.find((d) => d.id === device.id)) {
          log(`Already sent to ${device.name || "Unknown Device"}`, "info");
          continue;
        }

        log(`Connecting to ${device.name || "Unknown Device"}...`);

        try {
          const server = await device.gatt.connect();
          const service = await server.getPrimaryService(BITCHAT_SERVICE_UUID);
          const characteristic = await service.getCharacteristic(
            BITCHAT_CHAR_UUID
          );

          log("Sending announce packet...");
          const announcePacket = generateAnnouncePacket(senderId, senderName);
          await characteristic.writeValueWithoutResponse(announcePacket);
          await new Promise((resolve) => setTimeout(resolve, 500));

          for (let i = 0; i < numMessages; i++) {
            log(
              `Sending message ${i + 1}/${numMessages} to ${
                device.name || "Device"
              }...`
            );
            const messagePacket = generateMessagePacket(
              senderId,
              senderName,
              message,
              5
            );
            await characteristic.writeValueWithoutResponse(messagePacket);
            await new Promise((resolve) => setTimeout(resolve, 500));
          }

          messagesSent += numMessages;
          devicesFound++;
          discoveredDevices.push(device);

          log(
            `✓ Sent ${numMessages} message(s) to ${device.name || "Device"}`,
            "success"
          );

          await server.disconnect();
        } catch (error) {
          log(
            `Failed to send to ${device.name || "Device"}: ${error.message}`,
            "error"
          );
        }
      } catch (error) {
        if (error.message.includes("User cancelled")) {
          log("User cancelled device selection", "info");
          continueBroadcast = false;
        } else {
          log(`Error: ${error.message}`, "error");
          continueBroadcast = false;
        }
      }
    }

    if (devicesFound > 0) {
      log(
        `Broadcast complete! Sent ${messagesSent} message(s) to ${devicesFound} device(s)`,
        "success"
      );
      setStatus(`Broadcast to ${devicesFound} devices`, "connected");
    } else {
      setStatus("No devices found", "disconnected");
    }

    discoveredDevices = [];
  } catch (error) {
    log(`Broadcast error: ${error.message}`, "error");
    setStatus("Broadcast failed", "disconnected");
  } finally {
    document.getElementById("broadcastBtn").disabled = false;
  }
}
document
  .getElementById("broadcastBtn")
  .addEventListener("click", broadcastToAll);

function parseReceivedPacket(data) {
  const view = new DataView(data.buffer);
  const uint8View = new Uint8Array(data.buffer);
  let offset = 0;

  try {
    const packetType1 = view.getUint8(offset++);
    const packetType2 = view.getUint8(offset++);

    if (packetType1 === 0x01 && packetType2 === 0x01) {
      const ttl = view.getUint8(offset++);
      const timestamp = Number(view.getBigUint64(offset, false));
      offset += 8;

      offset++;

      const nameLength = view.getUint16(offset, false);
      offset += 2;

      const senderId = uint8View.slice(offset, offset + 8);
      offset += 8;

      const decoder = new TextDecoder();
      const senderName = decoder.decode(
        uint8View.slice(offset, offset + nameLength)
      );

      return {
        type: "announce",
        senderName,
        senderId: Array.from(senderId)
          .map((b) => b.toString(16).padStart(2, "0"))
          .join(""),
        timestamp: new Date(timestamp),
      };
    } else if (packetType1 === 0x01 && packetType2 === 0x04) {
      const ttl = view.getUint8(offset++);
      const timestamp = Number(view.getBigUint64(offset, false));
      offset += 8;

      offset++;

      const messageLength = view.getUint16(offset, false);
      offset += 2;

      const senderId = uint8View.slice(offset, offset + 8);
      offset += 8;

      offset += 8;

      let msgOffset = offset;
      const msgFlags = view.getUint8(msgOffset++);
      const msgTimestamp = Number(view.getBigUint64(msgOffset, false));
      msgOffset += 8;

      const uidLength = view.getUint8(msgOffset++);
      const decoder = new TextDecoder();
      const uid = decoder.decode(
        uint8View.slice(msgOffset, msgOffset + uidLength)
      );
      msgOffset += uidLength;

      const nameLength = view.getUint8(msgOffset++);
      const senderName = decoder.decode(
        uint8View.slice(msgOffset, msgOffset + nameLength)
      );
      msgOffset += nameLength;

      const contentLength = view.getUint16(msgOffset, false);
      msgOffset += 2;
      const content = decoder.decode(
        uint8View.slice(msgOffset, msgOffset + contentLength)
      );
      msgOffset += contentLength;

      const senderIdLength = view.getUint8(msgOffset++);
      const messageSenderId = uint8View.slice(
        msgOffset,
        msgOffset + senderIdLength
      );

      return {
        type: "message",
        senderName,
        content,
        senderId: Array.from(senderId)
          .map((b) => b.toString(16).padStart(2, "0"))
          .join(""),
        timestamp: new Date(msgTimestamp),
        uid,
      };
    }

    return null;
  } catch (error) {
    console.error("Error parsing packet:", error);
    return null;
  }
}

function displayReceivedMessage(message) {
  const messagesSection = document.getElementById("messagesSection");
  const messagesContainer = document.getElementById("receivedMessages");

  messagesSection.style.display = "block";

  const messageEl = document.createElement("div");
  messageEl.className = "received-message";

  if (message.type === "announce") {
    messageEl.innerHTML = `
            <div class="sender">${message.senderName} joined</div>
            <div class="content">User announced presence</div>
            <div class="timestamp">${message.timestamp.toLocaleTimeString()}</div>
        `;
  } else if (message.type === "message") {
    messageEl.innerHTML = `
            <div class="sender">${message.senderName}</div>
            <div class="content">${message.content}</div>
            <div class="timestamp">${message.timestamp.toLocaleTimeString()}</div>
        `;
  }

  messagesContainer.insertBefore(messageEl, messagesContainer.firstChild);

  if (messagesContainer.children.length > 50) {
    messagesContainer.removeChild(messagesContainer.lastChild);
  }
}

function handleCharacteristicValueChanged(event) {
  const value = event.target.value;
  const message = parseReceivedPacket(value);

  if (message) {
    log(`Received ${message.type} from ${message.senderName}`, "success");
    displayReceivedMessage(message);
  }
}

async function startListening() {
  if (!currentCharacteristic) {
    log("Not connected to any device", "error");
    return;
  }

  try {
    if (!isListening) {
      const properties = currentCharacteristic.properties;

      if (properties.notify || properties.indicate) {
        await currentCharacteristic.startNotifications();
        currentCharacteristic.addEventListener(
          "characteristicvaluechanged",
          handleCharacteristicValueChanged
        );

        isListening = true;
        listenBtn.textContent = "Stop Listening";
        log("Started listening for messages", "success");

        document.getElementById("messagesSection").style.display = "block";
      } else {
        log("This characteristic does not support notifications", "error");
        log("Trying to read value directly...", "info");

        if (properties.read) {
          const value = await currentCharacteristic.readValue();
          const message = parseReceivedPacket(value);
          if (message) {
            displayReceivedMessage(message);
          }
        } else {
          log(
            "Cannot receive messages - characteristic does not support read or notify",
            "error"
          );
        }
      }
    } else {
      if (
        currentCharacteristic.properties.notify ||
        currentCharacteristic.properties.indicate
      ) {
        await currentCharacteristic.stopNotifications();
        currentCharacteristic.removeEventListener(
          "characteristicvaluechanged",
          handleCharacteristicValueChanged
        );
      }

      isListening = false;
      listenBtn.textContent = "Start Listening";
      log("Stopped listening for messages", "info");
    }
  } catch (error) {
    log(`Failed to start/stop listening: ${error.message}`, "error");
  }
}
document.getElementById("listenBtn").addEventListener("click", startListening);

if (!navigator.bluetooth) {
  setStatus("Bluetooth not supported", "disconnected");
  log("Web Bluetooth API is not available in this browser", "error");
  scanBtn.disabled = true;
  document.getElementById("broadcastBtn").disabled = true;
  listenBtn.disabled = true;
}
