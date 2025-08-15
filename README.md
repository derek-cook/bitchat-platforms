
# bitchat-platforms

A collection of apps that aim to be interoperable with the [bitchat](https://github.com/permissionlesstech/bitchat/tree/main) mobile app.

The purpose is to explore different ways of communicating over bluetooth in a decentralized, offline way. 

This is an ***experimental*** proof of concept. Please note:
* Feature parity with the mobile app is very low. Some assumptions here are not correct about how bitchat works.
* I intentionally used as few libraries as possible to keep the focus on the capabilities of the platform itself.
* Don't use in situations that are sensitive to security or privacy. Bluetooth communication works as-is without encryption.

### What works ✅
- **Broadcast message**: Send to all -> for each nearby bitchat device: connect, send, and disconnect.
* **Send to device**: Connect to Device -> Send to connected -> sends and retains connection.  
* **Listen to device**: Connect to Device -> Start Listening -> receives messages from that device

### Needs work ⚠️
* **Direct Messages**: Saved contacts (Network bar in the mobile app) is not implemented. Direct messages, although sent only to the connected device, show in the main chat rather than in a separate DM window.
* **Connection prompt**: The PWA requires an explicit device select prompt due to browser security restrictions. This might be ok if it can use a helper app or relay via another single device.
* **Broadcast connections**: This isn't quite a "mesh" network. Ideally it would require one connection and relay messages rather than repeating the process for each nearby device.
* **Encryption/Handshake**: not implemented

## Electron
To run locally
```
npx electron ./bitchat-electron/main.js
```
\
Considerations
* Uses the Web Bluetooth api and electron api.
* Some operating systems require a pin to confirm connection.
* The electron api allows you to connect to devices without a device select prompt (unlike in a browser), so if you want that control you'll have to bring your own UI.


## PWA (progressive web app)
To run locally at `https://localhost:8443`
```
./bitchat-pwa/server.py
```
\
Considerations
* Browser apps can only act as clients, so they lack the ability to advertise as a gatt server.
* BT connections require https.
* An initial visit online is required to cache files for offline use.
* Service workers don't have access to the bluetooth api.
* `bitchatFunctions.js` and `index.html` are essentially duplicated from the electron app for isolation purposes.


## To explore
* IoT/microcontrollers - Devices like an ESP32 are pretty easy to implement BT features on. You'd need some interface (keyboard/display), but you can get a proof of concept with some hardcoding and serial monitor. There's some interesting related work on Meshtastic/LoRa/BLE mesh.
* a bitchat CLI - initial use of a python script seems promising, see [bitchat-spam](https://github.com/BrownFineSecurity/bitchat-spam)
* security/anti-spam, especially for scripts.
