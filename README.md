
# bitchat-platforms

A collection of apps that aim to be interoperable with the [bitchat](https://github.com/permissionlesstech/bitchat/tree/main) mobile app.

The purpose is to explore different ways of communicating over bluetooth in a decentralized, offline way. 

This is an ***experimental*** proof of concept. Feature parity with the mobile app is not 100%. Security may be flawed, and other features like encryption are not yet implemented. The following notes may have some incorrect assumptions

## Electron
What works ✅
* Can send messages to multiple nearby device running the bitchat iOS app without a connection prompt.
What doesn't work yet ⚠️
* Has to explicitly connect to a nearby device to listen and receive messages.
* Direct messaging
Considerations
* The electron api allows you to connect to devices without a user prompt (like in the web app), so if you want that control you'll have to bring your own UI.
* Uses the Web Bluetooth api.
* Some operating systems require a pin to confirm connection.


## PWA (progressive web app)
Honestly this one is impractical so far due to browser security limitations.
What works ✅
* After a browser prompt to connect, you can send a message to one device at a time.
What doesn't work yet ⚠️
* pretty much everything else
Considerations
* Service workers don't have access to the bluetooth api.
* The BT connection requires https.
* An initial visit online is required to cache files for offline use.


## Cases to explore
* IoT/microcontrollers - Devices like an ESP32 are pretty easy to implement BT features on. You'd need some interface to type/display, but a PoC can use a sketch with some hardcoding. There's some interesting related work on Meshtastic/LoRa/BLE mesh.
* a bitchat CLI - initial use of a python script seems promising, see [bitchat-spam](https://github.com/BrownFineSecurity/bitchat-spam)
* security/anti-spam, especially for scripts.
* app clips
